"""Identity resolution node.

Responsibility: establish (or honestly decline to establish) which protein this
sequence is. curie's UniProt client does not implement exact-sequence matching
(that requires a job-based alignment service, out of scope for this phase — see
docs/LIMITATIONS.md) so the only path to a resolved identity right now is a
caller-supplied `accession_hint`, confirmed by a real UniProt lookup on it.

Absent a hint, this node does NOT fall back to a keyword/text search on the
sequence and treat a plausible-looking hit as identity — that would be exactly
the "no exact match found" -> "this is protein X" hallucination this project
exists to avoid. It sets identity_status=UNRESOLVED and records that as a
first-class piece of evidence (ABSENCE_OF_EVIDENCE), not a silent gap.
"""

from __future__ import annotations

import time

from curie.agent.state import InvestigationState
from curie.shared.logging import get_logger
from curie.shared.models import (
    CandidateProtein,
    Directness,
    EvidenceLevel,
    EvidenceRecord,
    EvidenceType,
    IdentityStatus,
    TraceEvent,
)
from curie.tools.uniprot import UniProtClient

logger = get_logger(__name__)

NODE_NAME = "identity_resolution"


def _extract_protein_name(entry: dict) -> str | None:
    return (
        entry.get("proteinDescription", {})
        .get("recommendedName", {})
        .get("fullName", {})
        .get("value")
    )


async def identity_resolution(state: InvestigationState) -> dict:
    start = time.perf_counter()
    tools_called: list[str] = []

    if not state.accession_hint:
        duration_ms = (time.perf_counter() - start) * 1000
        evidence = EvidenceRecord(
            source="curie",
            source_type="internal",
            claim="No accession hint supplied; sequence-based identity resolution "
            "is not implemented, so identity could not be established.",
            evidence_type=EvidenceType.ABSENCE_OF_EVIDENCE,
            evidence_level=EvidenceLevel.NONE,
            directness=Directness.UNKNOWN,
        )
        trace = TraceEvent(
            run_id=state.run_id,
            node=NODE_NAME,
            duration_ms=duration_ms,
            status="ok",
            tools_called=tools_called,
            input_summary="no accession_hint",
            output_summary="identity_status=UNRESOLVED",
            evidence_count=1,
        )
        logger.info("identity_resolution", run_id=state.run_id, resolved=False)
        return {
            "identity_status": IdentityStatus.UNRESOLVED,
            "evidence": [evidence],
            "trace": [trace],
        }

    client = UniProtClient()
    tools_called.append("uniprot")
    result = await client.get_entry(state.accession_hint)

    identity_status = IdentityStatus.UNRESOLVED
    protein_name: str | None = None
    candidates: list[CandidateProtein] = []

    # `result.ok` only means the HTTP call succeeded — a 200 response can still
    # carry a payload that isn't the dict shape we expect (an empty body, a
    # bare list, a different schema version). Treat that as a failed
    # resolution rather than letting .get() crash the node and take the whole
    # graph run down with it.
    malformed = result.ok and not isinstance(result.data, dict)

    if result.ok and not malformed:
        protein_name = _extract_protein_name(result.data)
        organism = result.data.get("organism", {}).get("scientificName")
        candidates.append(
            CandidateProtein(
                accession=state.accession_hint,
                name=protein_name,
                organism=organism,
                match_type="accession_hint",
            )
        )
        identity_status = IdentityStatus.RESOLVED_HINT
        evidence = EvidenceRecord(
            source="uniprot",
            source_type="database",
            identifier=state.accession_hint,
            claim=f"UniProt accession {state.accession_hint} resolves to "
            f"'{protein_name}'" + (f" ({organism})" if organism else ""),
            evidence_type=EvidenceType.CURATED_ANNOTATION,
            evidence_level=EvidenceLevel.CURATED,
            directness=Directness.DIRECT,
            source_url=f"https://www.uniprot.org/uniprotkb/{state.accession_hint}",
            metadata={"raw": result.data},
        )
    elif malformed:
        evidence = EvidenceRecord(
            source="uniprot",
            source_type="database",
            identifier=state.accession_hint,
            claim=f"UniProt returned an unexpected (non-object) response shape "
            f"for accession hint '{state.accession_hint}'; treating as unresolved "
            f"rather than guessing at its structure.",
            evidence_type=EvidenceType.ABSENCE_OF_EVIDENCE,
            evidence_level=EvidenceLevel.NONE,
            directness=Directness.DIRECT,
        )
    else:
        evidence = EvidenceRecord(
            source="uniprot",
            source_type="database",
            identifier=state.accession_hint,
            claim=f"UniProt lookup for accession hint '{state.accession_hint}' "
            f"failed: {result.error}",
            evidence_type=EvidenceType.ABSENCE_OF_EVIDENCE,
            evidence_level=EvidenceLevel.NONE,
            directness=Directness.DIRECT,
        )

    resolved = identity_status == IdentityStatus.RESOLVED_HINT
    duration_ms = (time.perf_counter() - start) * 1000
    trace = TraceEvent(
        run_id=state.run_id,
        node=NODE_NAME,
        duration_ms=duration_ms,
        status="ok" if resolved else "error",
        tools_called=tools_called,
        input_summary=f"accession_hint={state.accession_hint}",
        output_summary=f"identity_status={identity_status.value}, protein_name={protein_name}",
        evidence_count=1,
        errors=[]
        if resolved
        else [
            "uniprot returned a malformed (non-object) response"
            if malformed
            else (result.error or "uniprot lookup failed")
        ],
    )

    logger.info(
        "identity_resolution",
        run_id=state.run_id,
        resolved=resolved,
        malformed=malformed,
        identity_status=identity_status.value,
    )

    return {
        "identity_status": identity_status,
        "candidate_proteins": candidates,
        "protein_name": protein_name,
        "tool_results": [result],
        "evidence": [evidence],
        "trace": [trace],
    }
