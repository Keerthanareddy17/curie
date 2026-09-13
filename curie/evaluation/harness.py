"""Evaluation harness: run the agent graph over a batch of fixture cases and report
each one's evidence score and final status.

This actually executes the real graph (real network calls to ESM Atlas / UniProt /
IEDB / Europe PMC) — it is not a mock runner. For fully offline/deterministic
testing, unit tests exercise `curie.evaluation.reliability.score_run` and the
graph nodes directly against fixture data instead (see tests/test_reliability.py,
tests/test_graph_e2e.py).
"""

from __future__ import annotations

from curie.agent.graph import run_investigation
from curie.evaluation.models import EvaluationCase, EvaluationCaseResult
from curie.shared.logging import get_logger

logger = get_logger(__name__)


async def run_case(case: EvaluationCase) -> EvaluationCaseResult:
    state = await run_investigation(case.sequence, accession_hint=case.accession_hint)
    evidence_score = state.evidence_score or 0.0

    passed: bool | None = None
    notes_parts: list[str] = []
    if case.expect_min_evidence_score is not None:
        ok = evidence_score >= case.expect_min_evidence_score
        passed = ok if passed is None else (passed and ok)
        notes_parts.append(f"evidence_score={evidence_score} expected>={case.expect_min_evidence_score}")
    if case.expect_status is not None:
        ok = state.status == case.expect_status
        passed = ok if passed is None else (passed and ok)
        notes_parts.append(f"status={state.status.value} expected={case.expect_status.value}")

    return EvaluationCaseResult(
        case_id=case.case_id,
        run_id=state.run_id,
        evidence_score=evidence_score,
        status=state.status,
        passed=passed,
        notes="; ".join(notes_parts),
    )


async def run_suite(cases: list[EvaluationCase]) -> list[EvaluationCaseResult]:
    results = []
    for case in cases:
        logger.info("evaluation_case_start", case_id=case.case_id)
        results.append(await run_case(case))
    return results
