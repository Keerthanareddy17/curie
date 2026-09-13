"""Node-level tests for research_planner's optional Gemini integration.

Covers the explicit regression list: Gemini unavailable, deterministic
fallback, and confirms `needs_identity`/`structure_allowed` are never
influenced by Gemini (they're safety/fact fields, not suggestions).
"""

from __future__ import annotations

from curie.agent.nodes.research_planner import research_planner
from curie.agent.state import InvestigationState
from curie.shared.models import ToolResult, ToolStatus
from curie.tools.gemini import GeminiClient


def _ok_gemini_result(**overrides) -> ToolResult:
    data = {
        "needs_epitope_evidence": False,
        "needs_literature": False,
        "needs_structure": True,
        "reasoning": "Gemini-provided plan.",
        **overrides,
    }
    return ToolResult(provider="gemini", operation="planner", status=ToolStatus.OK, latency_ms=5.0, data=data)


async def test_planner_falls_back_deterministically_without_api_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    state = InvestigationState(raw_sequence="X", normalized_sequence="M" * 50)

    update = await research_planner(state)

    plan = update["research_plan"]
    assert plan.needs_epitope_evidence is True  # deterministic default, not Gemini's
    assert plan.needs_literature is True
    assert update["tool_results"] == []  # Gemini never called at all without a key


async def test_planner_uses_gemini_suggestion_when_available(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")

    async def fake_plan_research(self, sequence_type, sequence_length, accession_hint):
        return _ok_gemini_result(needs_epitope_evidence=False, needs_literature=False)

    monkeypatch.setattr(GeminiClient, "plan_research", fake_plan_research)

    state = InvestigationState(raw_sequence="X", normalized_sequence="M" * 50)
    update = await research_planner(state)

    plan = update["research_plan"]
    assert plan.needs_epitope_evidence is False
    assert plan.needs_literature is False
    assert plan.reasoning == "Gemini-provided plan."
    assert len(update["tool_results"]) == 1
    assert update["tool_results"][0].provider == "gemini"


async def test_planner_needs_identity_is_never_influenced_by_gemini(monkeypatch):
    """needs_identity is a fact (was a hint supplied?), not a judgment call —
    Gemini's schema doesn't even include this field (see ResearchPlanSuggestion)."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")

    async def fake_plan_research(self, sequence_type, sequence_length, accession_hint):
        return _ok_gemini_result()

    monkeypatch.setattr(GeminiClient, "plan_research", fake_plan_research)

    state_with_hint = InvestigationState(raw_sequence="X", normalized_sequence="M" * 50, accession_hint="P0DTC2")
    update = await research_planner(state_with_hint)
    assert update["research_plan"].needs_identity is False

    state_without_hint = InvestigationState(raw_sequence="X", normalized_sequence="M" * 50)
    update2 = await research_planner(state_without_hint)
    assert update2["research_plan"].needs_identity is True


async def test_planner_structure_allowed_is_never_influenced_by_gemini(monkeypatch):
    """structure_allowed is a hard safety fact from sequence length — even if
    Gemini's needs_structure=True, a >400aa sequence must still be structure_allowed=False."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")

    async def fake_plan_research(self, sequence_type, sequence_length, accession_hint):
        return _ok_gemini_result(needs_structure=True)

    monkeypatch.setattr(GeminiClient, "plan_research", fake_plan_research)

    state = InvestigationState(raw_sequence="X", normalized_sequence="M" * 500)
    update = await research_planner(state)

    assert update["research_plan"].structure_allowed is False


async def test_planner_falls_back_deterministically_when_gemini_call_fails(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")

    async def fake_plan_research(self, sequence_type, sequence_length, accession_hint):
        return ToolResult(
            provider="gemini", operation="planner", status=ToolStatus.ERROR, latency_ms=5.0, error="503"
        )

    monkeypatch.setattr(GeminiClient, "plan_research", fake_plan_research)

    state = InvestigationState(raw_sequence="X", normalized_sequence="M" * 50)
    update = await research_planner(state)

    plan = update["research_plan"]
    assert plan.needs_epitope_evidence is True  # deterministic fallback used
    assert plan.needs_literature is True
    assert "structure_allowed=" in plan.reasoning  # deterministic reasoning string, not a fabricated one
    assert len(update["tool_results"]) == 1  # the failed attempt is still recorded, not hidden
    assert update["tool_results"][0].status == ToolStatus.ERROR
