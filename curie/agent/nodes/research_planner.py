"""Research planner node.

Responsibility: decide WHAT TO LOOK FOR, never WHAT IS TRUE.

`needs_identity` and `structure_allowed` are always computed deterministically
from the sequence itself (whether an accession hint was supplied; whether the
normalized length is within ESM Atlas's fold limit) — these are facts, not
judgment calls, and Gemini is never consulted on them. When `GEMINI_API_KEY`
is configured, Gemini is additionally asked for `needs_epitope_evidence`,
`needs_literature`, `needs_structure`, and a plain-language `reasoning`
string; without a key, or if the call fails or returns malformed structured
output, those fields fall back to the exact same deterministic defaults this
node used before Gemini existed (`True`/`True`/`length > 0`) — Gemini is
advisory here, never a single point of failure, and downstream nodes
(structure_prediction, epitope_evidence, literature_check) independently
re-check their own real preconditions regardless of what this plan says, so
a wrong or missing suggestion here cannot cause a tool to run unsafely.
"""

from __future__ import annotations

import time

from curie.agent.state import InvestigationState
from curie.shared.config import get_settings
from curie.shared.logging import get_logger
from curie.shared.models import InvestigationStatus, ResearchPlan, ToolResult, TraceEvent
from curie.tools.esm_atlas import MAX_SEQUENCE_LENGTH

logger = get_logger(__name__)

NODE_NAME = "research_planner"


def _deterministic_reasoning(sequence_type: str, sequence_length: int, accession_hint: str | None, structure_allowed: bool) -> str:
    return (
        f"sequence_type={sequence_type}, length={sequence_length}, "
        f"accession_hint={'provided' if accession_hint else 'absent'}, "
        f"structure_allowed={structure_allowed} (limit={MAX_SEQUENCE_LENGTH} aa)"
    )


async def research_planner(state: InvestigationState) -> dict:
    start = time.perf_counter()

    sequence_length = len(state.normalized_sequence)
    structure_allowed = 0 < sequence_length <= MAX_SEQUENCE_LENGTH
    needs_identity = state.accession_hint is None

    needs_epitope_evidence = True
    needs_literature = True
    needs_structure = sequence_length > 0
    reasoning = _deterministic_reasoning(
        state.sequence_type.value, sequence_length, state.accession_hint, structure_allowed
    )

    tool_results: list[ToolResult] = []
    settings = get_settings()
    if settings.gemini_api_key:
        from curie.tools.gemini import GeminiClient

        client = GeminiClient(api_key=settings.gemini_api_key, model=settings.gemini_model)
        gemini_result = await client.plan_research(
            sequence_type=state.sequence_type.value,
            sequence_length=sequence_length,
            accession_hint=state.accession_hint,
        )
        tool_results.append(gemini_result)
        if gemini_result.ok:
            suggestion = gemini_result.data
            needs_epitope_evidence = suggestion["needs_epitope_evidence"]
            needs_literature = suggestion["needs_literature"]
            needs_structure = suggestion["needs_structure"] and sequence_length > 0
            reasoning = suggestion["reasoning"]
        else:
            logger.info(
                "research_planner_gemini_fallback",
                run_id=state.run_id,
                status=gemini_result.status.value,
                error=gemini_result.error,
            )

    plan = ResearchPlan(
        needs_identity=needs_identity,
        needs_epitope_evidence=needs_epitope_evidence,
        needs_literature=needs_literature,
        needs_structure=needs_structure,
        structure_allowed=structure_allowed,
        reasoning=reasoning,
    )

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info("research_planner", run_id=state.run_id, plan=plan.model_dump())

    trace = TraceEvent(
        run_id=state.run_id,
        node=NODE_NAME,
        duration_ms=duration_ms,
        status="ok",
        tools_called=["gemini"] if tool_results else [],
        input_summary=f"normalized_length={sequence_length}",
        output_summary=plan.reasoning,
    )

    return {
        "research_plan": plan,
        "status": InvestigationStatus.COLLECTING,
        "tool_results": tool_results,
        "trace": [trace],
    }
