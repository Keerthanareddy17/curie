"""Gemini synthesis node.

Responsibility: narrate the ALREADY-FIXED deterministic evidence in plain
language. Runs after confidence_gate, so evidence_score, status, claims, and
conflicts are all finalized before Gemini ever sees them — this node's output
(`ai_synthesis`, a single string) is purely descriptive and cannot feed back
into any of those fields. Only the deterministic evidence graph — never raw
tool payloads, never free interpretation — is given to Gemini, and the system
instruction (curie/tools/gemini.py) explicitly forbids inventing evidence,
upgrading indirect evidence to direct, or resolving conflicts by guessing.

Entirely optional: without `GEMINI_API_KEY`, or if the call fails, times out,
or returns malformed output, `ai_synthesis` stays `None` and the dossier is
still generated in full from structured state alone, exactly as in Phase 3 —
this node changes nothing about curie's ability to produce a deterministic,
fully-evidenced dossier on its own.
"""

from __future__ import annotations

import time

from curie.agent.state import InvestigationState
from curie.shared.config import get_settings
from curie.shared.logging import get_logger
from curie.shared.models import ToolResult, ToolStatus, TraceEvent

logger = get_logger(__name__)

NODE_NAME = "gemini_synthesis"


def _build_evidence_summary(state: InvestigationState) -> str:
    lines = [
        f"Sequence type: {state.sequence_type.value}, length: {len(state.normalized_sequence)} aa",
        f"Identity status: {state.identity_status.value}"
        + (f" ({state.protein_name})" if state.protein_name else ""),
        f"Final status (already decided, do not contradict): {state.status.value}",
        f"Evidence score (already decided, do not restate as a probability): {state.evidence_score}",
        "",
        "Evidence records retrieved:",
    ]
    for e in state.evidence:
        lines.append(
            f"- [{e.source}] type={e.evidence_type.value} level={e.evidence_level.value} "
            f"directness={e.directness.value}: {e.claim}"
        )
    lines.append("")
    lines.append("Cross-source adjudication claims (already decided):")
    for c in state.claims:
        lines.append(f"- {c.statement} -> {c.agreement.value}")
    if state.conflicts:
        lines.append("")
        lines.append("Unresolved conflicts (already decided, describe but do not resolve):")
        for conflict in state.conflicts:
            lines.append(f"- {conflict.claim} (severity: {conflict.severity})")
    if state.missing_evidence:
        lines.append("")
        lines.append("Missing evidence (state plainly, do not paper over):")
        for m in state.missing_evidence:
            lines.append(f"- {m}")
    return "\n".join(lines)


async def gemini_synthesis(state: InvestigationState) -> dict:
    start = time.perf_counter()
    settings = get_settings()

    if not settings.gemini_api_key:
        result = ToolResult(
            provider="gemini",
            operation="synthesis",
            status=ToolStatus.SKIPPED,
            latency_ms=0.0,
            error="GEMINI_API_KEY not configured",
        )
        duration_ms = (time.perf_counter() - start) * 1000
        return {
            "ai_synthesis": None,
            "tool_results": [result],
            "trace": [
                TraceEvent(
                    run_id=state.run_id,
                    node=NODE_NAME,
                    duration_ms=duration_ms,
                    status="skipped",
                    output_summary="Gemini synthesis skipped: no API key configured.",
                )
            ],
        }

    from curie.tools.gemini import GeminiClient

    client = GeminiClient(api_key=settings.gemini_api_key, model=settings.gemini_model)
    summary = _build_evidence_summary(state)
    result = await client.synthesize(summary)

    ai_synthesis = result.data["narrative"] if result.ok else None

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info("gemini_synthesis", run_id=state.run_id, status=result.status.value)

    trace = TraceEvent(
        run_id=state.run_id,
        node=NODE_NAME,
        duration_ms=duration_ms,
        status=result.status.value,
        tools_called=["gemini"],
        input_summary=f"{len(state.evidence)} evidence record(s), {len(state.claims)} claim(s)",
        output_summary="narrative generated" if ai_synthesis else f"unavailable: {result.error}",
        errors=[] if result.ok else [result.error or "gemini synthesis failed"],
    )

    return {
        "ai_synthesis": ai_synthesis,
        "tool_results": [result],
        "trace": [trace],
    }
