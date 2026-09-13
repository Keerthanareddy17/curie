"""Node-level tests for gemini_synthesis.

Covers: Gemini unavailable, synthesis failure, grounded synthesis on success,
and — most importantly — that this node structurally cannot touch the
deterministic fields (evidence_score, status, conflicts, claims, provenance)
that confidence_gate already fixed before this node ever runs.
"""

from __future__ import annotations

from curie.agent.nodes.gemini_synthesis import gemini_synthesis
from curie.agent.state import InvestigationState
from curie.shared.models import Claim, EvidenceConflict, InvestigationStatus, ToolResult, ToolStatus
from curie.tools.gemini import GeminiClient

# tool_results IS touched (this node appends its own ToolResult, same as
# every other tool-calling node) — but only appended to, never replacing an
# existing entry, and never altering evidence_score/status/conflicts/claims.
PROTECTED_FIELDS = {"evidence_score", "status", "conflicts", "claims"}


def _state_with_fixed_result() -> InvestigationState:
    return InvestigationState(
        raw_sequence="MKV",
        status=InvestigationStatus.SUPPORTED,
        evidence_score=0.91,
        claims=[Claim(statement="fixed claim", agreement="agree")],
        conflicts=[
            EvidenceConflict(
                claim="fixed conflict", evidence_a="a", evidence_b="b",
                conflict_type="x", severity="low", resolved=True,
            )
        ],
    )


async def test_synthesis_skipped_without_api_key_leaves_ai_synthesis_none(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    state = _state_with_fixed_result()

    update = await gemini_synthesis(state)

    assert update["ai_synthesis"] is None
    assert update["tool_results"][0].status == ToolStatus.SKIPPED
    for field in PROTECTED_FIELDS:
        assert field not in update, f"gemini_synthesis must never set {field!r}"


async def test_synthesis_success_sets_narrative_without_touching_protected_fields(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")

    async def fake_synthesize(self, evidence_summary):
        assert "SUPPORTED" in evidence_summary or "supported" in evidence_summary
        return ToolResult(
            provider="gemini", operation="synthesis", status=ToolStatus.OK,
            latency_ms=5.0, data={"narrative": "All independent sources agree on identity and structure."},
        )

    monkeypatch.setattr(GeminiClient, "synthesize", fake_synthesize)

    state = _state_with_fixed_result()
    update = await gemini_synthesis(state)

    assert update["ai_synthesis"] == "All independent sources agree on identity and structure."
    for field in PROTECTED_FIELDS:
        assert field not in update, f"gemini_synthesis must never set {field!r}"


async def test_synthesis_failure_leaves_ai_synthesis_none_not_fabricated(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")

    async def fake_synthesize(self, evidence_summary):
        return ToolResult(
            provider="gemini", operation="synthesis", status=ToolStatus.ERROR, latency_ms=5.0, error="quota exceeded"
        )

    monkeypatch.setattr(GeminiClient, "synthesize", fake_synthesize)

    state = _state_with_fixed_result()
    update = await gemini_synthesis(state)

    assert update["ai_synthesis"] is None
    assert update["tool_results"][0].error == "quota exceeded"


async def test_evidence_summary_given_to_gemini_excludes_raw_tool_payloads(monkeypatch):
    """The synthesis prompt must contain only already-adjudicated, structured
    facts — never raw tool response payloads — so Gemini cannot 'discover'
    anything beyond what curie's deterministic pipeline already decided."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")
    captured = {}

    async def fake_synthesize(self, evidence_summary):
        captured["summary"] = evidence_summary
        return ToolResult(
            provider="gemini", operation="synthesis", status=ToolStatus.OK, latency_ms=5.0,
            data={"narrative": "ok"},
        )

    monkeypatch.setattr(GeminiClient, "synthesize", fake_synthesize)

    state = _state_with_fixed_result()
    await gemini_synthesis(state)

    assert "fixed claim" in captured["summary"]
    assert "0.91" in captured["summary"]
    assert "raw_tool_response" not in captured["summary"].lower()
