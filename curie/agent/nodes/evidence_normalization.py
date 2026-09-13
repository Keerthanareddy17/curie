"""Evidence normalization node.

Responsibility: the explicit join point where the three parallel collection
branches (structure_prediction, epitope_evidence, literature_check) converge
before adjudication. Declared with `defer=True` in the graph so it runs exactly
once, after every branch has completed, regardless of how many hops deep each
branch was — see agent/graph.py for why that matters (structure_prediction is
one hop from the planner; epitope_evidence/literature_check are two, via
identity_resolution).

Every EvidenceRecord is already normalized at the point each collection node
creates it (they all construct the same Pydantic model), so this node's real job
is to be the single place that confirms the evidence pool is well-formed before
adjudication reads it — a validation seam, not just a rename.
"""

from __future__ import annotations

import time

from curie.agent.state import InvestigationState
from curie.shared.logging import get_logger
from curie.shared.models import TraceEvent

logger = get_logger(__name__)

NODE_NAME = "evidence_normalization"


def evidence_normalization(state: InvestigationState) -> dict:
    start = time.perf_counter()

    seen_ids: set[str] = set()
    duplicate_ids: list[str] = []
    for record in state.evidence:
        if record.evidence_id in seen_ids:
            duplicate_ids.append(record.evidence_id)
        seen_ids.add(record.evidence_id)

    errors = [f"duplicate evidence_id detected: {eid}" for eid in duplicate_ids]

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "evidence_normalization",
        run_id=state.run_id,
        evidence_count=len(state.evidence),
        tool_result_count=len(state.tool_results),
    )

    trace = TraceEvent(
        run_id=state.run_id,
        node=NODE_NAME,
        duration_ms=duration_ms,
        status="error" if errors else "ok",
        input_summary=f"{len(state.evidence)} evidence record(s) from "
        f"{len(state.tool_results)} tool call(s)",
        output_summary=f"{len(seen_ids)} unique evidence record(s)",
        evidence_count=len(state.evidence),
        errors=errors,
    )

    return {"errors": errors, "trace": [trace]}
