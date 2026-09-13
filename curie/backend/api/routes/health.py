"""Health endpoint.

Reports process liveness plus the package version — deliberately not a deep
dependency check (no outbound calls to ESM Atlas/UniProt/IEDB/Europe PMC here):
a health check that depends on four third-party services being up is a liveness
check for the internet, not for this process.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

import curie

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str
    time: str


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=curie.__version__,
        time=datetime.now(timezone.utc).isoformat(),
    )
