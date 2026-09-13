"""The investigation API contract for the frontend.

    POST   /api/investigations              -> {"run_id": "..."}   (starts, returns immediately)
    GET    /api/investigations/{run_id}      -> current InvestigationState
    GET    /api/investigations/{run_id}/trace   -> just the trace list
    GET    /api/investigations/{run_id}/dossier -> just the dossier (404 until ready)

A run in progress (state not yet in the store) returns a minimal
{"run_id", "status": "pending"} body from GET rather than 404, so a polling
frontend can distinguish "still running" from "never existed."
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from curie.backend.api.run_store import get_run, get_run_error, get_run_status, start_run
from curie.shared.models import Dossier, TraceEvent

router = APIRouter(prefix="/api/investigations")


class CreateInvestigationRequest(BaseModel):
    sequence: str
    accession_hint: str | None = None


class CreateInvestigationResponse(BaseModel):
    run_id: str


class PendingInvestigationResponse(BaseModel):
    run_id: str
    status: str


@router.post("", response_model=CreateInvestigationResponse)
async def create_investigation(request: CreateInvestigationRequest) -> CreateInvestigationResponse:
    run_id = start_run(request.sequence, accession_hint=request.accession_hint)
    return CreateInvestigationResponse(run_id=run_id)


@router.get("/{run_id}")
async def get_investigation(run_id: str):
    status = get_run_status(run_id)
    if status == "not_found":
        raise HTTPException(status_code=404, detail=f"no investigation with run_id {run_id!r}")
    if status == "failed":
        raise HTTPException(status_code=500, detail=get_run_error(run_id))
    if status == "pending":
        return PendingInvestigationResponse(run_id=run_id, status="pending")
    return get_run(run_id)


@router.get("/{run_id}/trace", response_model=list[TraceEvent])
async def get_investigation_trace(run_id: str) -> list[TraceEvent]:
    status = get_run_status(run_id)
    if status == "not_found":
        raise HTTPException(status_code=404, detail=f"no investigation with run_id {run_id!r}")
    if status in ("pending", "failed"):
        return []
    return get_run(run_id).trace


@router.get("/{run_id}/dossier", response_model=Dossier)
async def get_investigation_dossier(run_id: str) -> Dossier:
    status = get_run_status(run_id)
    if status == "not_found":
        raise HTTPException(status_code=404, detail=f"no investigation with run_id {run_id!r}")
    if status != "done":
        raise HTTPException(status_code=409, detail=f"investigation {run_id!r} is {status}, dossier not ready")
    dossier = get_run(run_id).dossier
    if dossier is None:
        raise HTTPException(status_code=500, detail="investigation completed without a dossier")
    return dossier
