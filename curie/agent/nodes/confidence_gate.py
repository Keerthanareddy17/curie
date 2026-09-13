"""Confidence / abstention gate.

Responsibility: turn the adjudicator's evidence_score and conflicts into one of
the fixed InvestigationStatus values, by explicit, reproducible rule — never a
model's judgment call. Abstention (INSUFFICIENT_EVIDENCE) is a normal, successful
outcome here, not a failure to route around.

Rules, in order:
1. FAILED: sequence_intake never produced a usable sequence. Nothing downstream
   could have run meaningfully.
2. CONFLICTING: any unresolved conflict exists between independent sources.
3. Otherwise, thresholds on evidence_score — capped at PARTIALLY_SUPPORTED
   when identity is unresolved, since curie will not call a conclusion
   SUPPORTED about a protein it cannot say the identity of.
"""

from __future__ import annotations

import time

from curie.agent.state import InvestigationState
from curie.shared.logging import get_logger
from curie.shared.models import IdentityStatus, InvestigationStatus, TraceEvent

logger = get_logger(__name__)

NODE_NAME = "confidence_gate"

SUPPORTED_THRESHOLD = 0.66
PARTIAL_THRESHOLD = 0.34


def _compute_status(state: InvestigationState) -> InvestigationStatus:
    if not state.normalized_sequence:
        return InvestigationStatus.FAILED

    if any(not conflict.resolved for conflict in state.conflicts):
        return InvestigationStatus.CONFLICTING

    score = state.evidence_score or 0.0

    if state.identity_status == IdentityStatus.UNRESOLVED:
        return (
            InvestigationStatus.PARTIALLY_SUPPORTED
            if score >= PARTIAL_THRESHOLD
            else InvestigationStatus.INSUFFICIENT_EVIDENCE
        )

    if score >= SUPPORTED_THRESHOLD:
        return InvestigationStatus.SUPPORTED
    if score >= PARTIAL_THRESHOLD:
        return InvestigationStatus.PARTIALLY_SUPPORTED
    return InvestigationStatus.INSUFFICIENT_EVIDENCE


def confidence_gate(state: InvestigationState) -> dict:
    start = time.perf_counter()
    status = _compute_status(state)
    duration_ms = (time.perf_counter() - start) * 1000

    logger.info("confidence_gate", run_id=state.run_id, status=status.value, evidence_score=state.evidence_score)

    trace = TraceEvent(
        run_id=state.run_id,
        node=NODE_NAME,
        duration_ms=duration_ms,
        status="ok",
        input_summary=f"evidence_score={state.evidence_score}, identity_status={state.identity_status.value}, "
        f"unresolved_conflicts={sum(1 for c in state.conflicts if not c.resolved)}",
        output_summary=f"status={status.value}",
        evidence_score=state.evidence_score,
    )

    return {"status": status, "trace": [trace]}
