"""Legacy investigation endpoint (Phase 1).

Kept for backward compatibility: runs the graph synchronously and returns the
full final state in one response. New clients should use `POST
/api/investigations` (curie/backend/api/routes/investigations.py), which
returns immediately with a run_id and supports polling for a long-running graph.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from curie.agent.graph import run_investigation
from curie.agent.state import InvestigationState

router = APIRouter()


class InvestigateRequest(BaseModel):
    sequence: str
    accession_hint: str | None = None


@router.post("/investigate", response_model=InvestigationState)
async def investigate(request: InvestigateRequest) -> InvestigationState:
    return await run_investigation(request.sequence, accession_hint=request.accession_hint)
