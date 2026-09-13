"""IEDB (Immune Epitope Database) IQ-API tool.

Real, public, no-key-required API (`query-api.iedb.org`), confirmed reachable during
inspection. This is the actual epitope evidence source Billie Gene's UI implied by
naming "IEDB-style" MHC-I/II scores but, per docs/ATTRIBUTION.md, never called —
`scanEpitopes()` in the upstream code is a self-contained anchor-residue heuristic,
not a query against IEDB.

Only a single, simple read operation is implemented here (search curated epitopes by
source antigen accession). IEDB's full API surface (T-cell/B-cell assay results,
the separate prediction-tools API for running MHC binding predictions) is out of
scope for this phase; those are natural follow-ups, not silently faked here.
"""

from __future__ import annotations

import httpx

from curie.shared.models import ToolResult
from curie.tools.base import BaseToolClient


class IedbClient(BaseToolClient):
    provider = "iedb"

    def __init__(self, base_url: str = "https://query-api.iedb.org", timeout_seconds: float = 20.0) -> None:
        super().__init__(base_url=base_url, timeout_seconds=timeout_seconds)

    async def search_epitopes_by_source_accession(
        self, accession: str, limit: int = 20
    ) -> ToolResult:
        """Look up curated epitopes whose source antigen matches a UniProt accession.

        `accession` should be a bare UniProt accession without version suffix
        (e.g. "P0DTC2"), matching how IEDB records `parent_source_antigen_iris`
        (e.g. "UNIPROT:P0DTC2") — confirmed against the live API during development.
        `data` is the parsed JSON list response from the IQ-API `epitope_search` view.
        """
        iri = f"UNIPROT:{accession}"

        async def _do_search(client: httpx.AsyncClient) -> list:
            response = await client.get(
                "/epitope_search",
                params={
                    "parent_source_antigen_iris": f"cs.{{{iri}}}",
                    "limit": limit,
                    "select": "structure_id,structure_descriptions,linear_sequence,"
                    "linear_sequence_length,parent_source_antigen_names,mhc_allele_names",
                },
            )
            response.raise_for_status()
            return response.json()

        return await self.call("search_epitopes_by_source_accession", _do_search)
