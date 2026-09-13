"""Europe PMC literature search tool.

Real, public, no-key-required API (`www.ebi.ac.uk/europepmc`), confirmed reachable
during inspection. Provides literature grounding — Billie Gene had no literature
lookup of any kind; its dossier text referenced databases like PharmGKB and ClinVar
only inside an LLM prompt, never actually queried.
"""

from __future__ import annotations

import httpx

from curie.shared.models import ToolResult
from curie.tools.base import BaseToolClient


class EuropePmcClient(BaseToolClient):
    provider = "europe_pmc"

    def __init__(
        self,
        base_url: str = "https://www.ebi.ac.uk/europepmc/webservices/rest",
        timeout_seconds: float = 20.0,
    ) -> None:
        super().__init__(base_url=base_url, timeout_seconds=timeout_seconds)

    async def search(self, query: str, page_size: int = 5) -> ToolResult:
        """Search Europe PMC. `data` is the parsed JSON response body."""

        async def _do_search(client: httpx.AsyncClient) -> dict:
            response = await client.get(
                "/search",
                params={"query": query, "format": "json", "pageSize": page_size},
            )
            response.raise_for_status()
            return response.json()

        return await self.call("search", _do_search)
