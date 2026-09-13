"""UniProtKB REST tool.

Real, public, no-key-required API (`rest.uniprot.org`), confirmed reachable during
inspection. Used for sequence/function annotation lookups — the "what is this
protein" grounding that Billie Gene's UI referenced (a hardcoded string
"UniProt_P0C6U8 (Consensus)") but never actually queried.
"""

from __future__ import annotations

import httpx

from curie.shared.models import ToolResult
from curie.tools.base import BaseToolClient


class UniProtClient(BaseToolClient):
    provider = "uniprot"

    def __init__(self, base_url: str = "https://rest.uniprot.org", timeout_seconds: float = 20.0) -> None:
        super().__init__(base_url=base_url, timeout_seconds=timeout_seconds)

    async def search(self, query: str, size: int = 5) -> ToolResult:
        """Free-text search of UniProtKB. `data` is the parsed JSON response body."""

        async def _do_search(client: httpx.AsyncClient) -> dict:
            response = await client.get(
                "/uniprotkb/search",
                params={"query": query, "format": "json", "size": size},
            )
            response.raise_for_status()
            return response.json()

        return await self.call("search", _do_search)

    async def get_entry(self, accession: str) -> ToolResult:
        """Fetch a single UniProtKB entry by accession (e.g. "P0DTC2")."""

        async def _do_get(client: httpx.AsyncClient) -> dict:
            response = await client.get(f"/uniprotkb/{accession}", params={"format": "json"})
            response.raise_for_status()
            return response.json()

        return await self.call("get_entry", _do_get)
