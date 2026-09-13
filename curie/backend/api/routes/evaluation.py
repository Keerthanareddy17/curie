"""Read-only access to the evaluation harness's last generated report.

Exposes the same JSON `python -m curie.evaluation.runner` already writes to
`curie/evaluation/results/latest.json` — no new computation happens here,
and nothing about a live investigation is mixed in. The frontend's
Reliability panel uses this to render benchmark numbers, clearly labeled as
"Evaluation benchmark" and never as metrics about the sequence a user just
submitted (see curie/evaluation/README.md and frontend section 19 of the
Phase 4 spec for why that distinction matters).
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/evaluation")

RESULTS_PATH = Path(__file__).resolve().parents[3] / "evaluation" / "results" / "latest.json"


@router.get("/latest")
async def get_latest_evaluation() -> dict:
    if not RESULTS_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="No evaluation report has been generated yet. Run "
            "`python -m curie.evaluation.runner` first.",
        )
    return json.loads(RESULTS_PATH.read_text())
