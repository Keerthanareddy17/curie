"""In-memory investigation run store.

A hackathon-scoped substitute for a real job queue/database: `POST
/api/investigations` returns a run_id immediately and kicks the graph off as a
background asyncio task; `GET /api/investigations/{run_id}` polls this store for
its current state. Polling is explicitly acceptable per project scope — no
websocket infrastructure. State is process-local and lost on restart, which is
fine for a single-process demo backend.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

from curie.agent.graph import run_investigation
from curie.agent.state import InvestigationState
from curie.shared.logging import get_logger

logger = get_logger(__name__)

_RUNS: dict[str, InvestigationState] = {}
_PENDING: set[str] = set()
_ERRORS: dict[str, str] = {}


def _new_run_id() -> str:
    return "inv-" + uuid4().hex[:12]


async def _execute(run_id: str, sequence: str, accession_hint: str | None) -> None:
    try:
        state = await run_investigation(sequence, accession_hint=accession_hint, run_id=run_id)
        _RUNS[run_id] = state
    except Exception as exc:  # noqa: BLE001 - reporting boundary for a background task
        logger.error("investigation_run_failed", run_id=run_id, error=str(exc))
        _ERRORS[run_id] = str(exc)
    finally:
        _PENDING.discard(run_id)


def start_run(sequence: str, accession_hint: str | None = None) -> str:
    run_id = _new_run_id()
    _PENDING.add(run_id)
    asyncio.create_task(_execute(run_id, sequence, accession_hint))
    return run_id


def get_run(run_id: str) -> InvestigationState | None:
    return _RUNS.get(run_id)


def get_run_status(run_id: str) -> str:
    """One of "pending", "done", "failed", or "not_found"."""
    if run_id in _RUNS:
        return "done"
    if run_id in _ERRORS:
        return "failed"
    if run_id in _PENDING:
        return "pending"
    return "not_found"


def get_run_error(run_id: str) -> str | None:
    return _ERRORS.get(run_id)
