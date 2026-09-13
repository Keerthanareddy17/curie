"""ESM Atlas ESMFold structure prediction tool.

Real, working, public API — no key required. Confirmed reachable during inspection
of the upstream Billie Gene project, which called the same endpoint client-side from
`Molecular3DVisualizer.tsx` / `App.tsx`. This is the one external integration Billie
Gene actually had; curie gives it a server-side, typed, logged home.

Endpoint contract (observed, not officially versioned beyond the URL path):
    POST https://api.esmatlas.com/foldSequence/v1/pdb/
    body: raw amino-acid sequence (no headers)
    response: PDB-format text on success
"""

from __future__ import annotations

import asyncio

import httpx

from curie.shared.logging import get_logger
from curie.shared.models import ToolResult
from curie.tools.base import BaseToolClient

MAX_SEQUENCE_LENGTH = 400  # ESMFold's public endpoint rejects longer inputs.
MAX_ATTEMPTS = 2  # bounded retry: one retry on a transient failure, no more.
RETRY_BACKOFF_SECONDS = 1.5

logger = get_logger(__name__)


def mean_plddt(pdb_text: str) -> float | None:
    """Mean per-residue confidence from an ESMFold PDB's B-factor column, on
    the conventional 0-100 pLDDT scale.

    ESMFold (like AlphaFold) repurposes the PDB B-factor field to carry
    predicted local distance difference test (pLDDT) confidence per atom —
    not invented, just read out of columns 61-66 of every ATOM record per the
    fixed-width PDB format. The public api.esmatlas.com endpoint was found
    (by inspecting a live response, not documentation) to emit this as a
    0.0-1.0 fraction rather than the conventional 0-100 percentage every
    other pLDDT consumer expects — confirmed via `curl` against a real fold
    during Phase 4 UI verification, where it rendered as a misleadingly tiny
    "0.2 pLDDT". Detected here by the same heuristic Billie Gene's original
    Molecular3DVisualizer.tsx used for the same ambiguity (max value <= ~1.5
    implies a fractional scale) and rescaled to 0-100 so the number means
    what pLDDT conventionally means. Returns None if no ATOM lines parse.
    """
    values: list[float] = []
    for line in pdb_text.splitlines():
        if not line.startswith("ATOM"):
            continue
        try:
            values.append(float(line[60:66]))
        except ValueError:
            continue
    if not values:
        return None
    if max(values) <= 1.5:
        values = [v * 100 for v in values]
    return sum(values) / len(values)


class EsmAtlasClient(BaseToolClient):
    provider = "esm_atlas"

    def __init__(self, base_url: str = "https://api.esmatlas.com", timeout_seconds: float = 60.0) -> None:
        super().__init__(base_url=base_url, timeout_seconds=timeout_seconds)

    async def fold_sequence(self, sequence: str) -> ToolResult:
        """Predict a 3D structure for a single-chain protein sequence.

        Returns a ToolResult whose `data` is raw PDB text on success. Sequences over
        `MAX_SEQUENCE_LENGTH` residues are rejected before any network call, mirroring
        the real limit of the public endpoint. Callers that already know a sequence is
        too long should skip calling this entirely (see agent/nodes/structure_prediction.py)
        rather than relying on this guard to report ERROR.

        Retries once on a timeout or 5xx server error before giving up; does not
        retry on 4xx (client error — retrying won't help) or a malformed response.
        """
        clean = "".join(sequence.split()).upper()

        async def _do_fold(client: httpx.AsyncClient) -> str:
            if len(clean) == 0:
                raise ValueError("sequence is empty")
            if len(clean) > MAX_SEQUENCE_LENGTH:
                raise ValueError(
                    f"sequence length {len(clean)} exceeds ESM Atlas public limit of {MAX_SEQUENCE_LENGTH}"
                )

            last_error: Exception | None = None
            for attempt in range(1, MAX_ATTEMPTS + 1):
                try:
                    response = await client.post("/foldSequence/v1/pdb/", content=clean)
                    response.raise_for_status()
                    pdb_text = response.text
                    if not pdb_text or not (
                        pdb_text.startswith("ATOM") or pdb_text.startswith("HEADER")
                    ):
                        raise ValueError("ESM Atlas returned an unrecognized (non-PDB) response")
                    return pdb_text
                except (httpx.TimeoutException, httpx.HTTPStatusError) as exc:
                    is_server_error = (
                        isinstance(exc, httpx.HTTPStatusError)
                        and exc.response.status_code < 500
                    )
                    if is_server_error or attempt == MAX_ATTEMPTS:
                        raise
                    last_error = exc
                    logger.info(
                        "esm_atlas_retry",
                        attempt=attempt,
                        max_attempts=MAX_ATTEMPTS,
                        error=str(exc),
                    )
                    await asyncio.sleep(RETRY_BACKOFF_SECONDS)
            raise last_error  # pragma: no cover - unreachable, loop always returns or raises

        return await self.call("fold_sequence", _do_fold)
