from curie.agent.nodes.literature_check import literature_check
from curie.agent.state import InvestigationState
from curie.shared.models import Directness, EvidenceType, ToolResult, ToolStatus
from curie.tools.europe_pmc import EuropePmcClient
from tests.fixtures.mock_responses import MOCK_EUROPE_PMC_SEARCH


def _state_with_name() -> InvestigationState:
    return InvestigationState(raw_sequence="MKV", protein_name="Spike glycoprotein")


async def test_literature_check_marks_results_indirect(monkeypatch):
    async def fake_search(self, query, page_size=5):
        return ToolResult(
            provider="europe_pmc",
            operation="search",
            status=ToolStatus.OK,
            latency_ms=10.0,
            data=MOCK_EUROPE_PMC_SEARCH,
        )

    monkeypatch.setattr(EuropePmcClient, "search", fake_search)

    update = await literature_check(_state_with_name())

    assert len(update["evidence"]) == 1
    evidence = update["evidence"][0]
    assert evidence.evidence_type == EvidenceType.LITERATURE
    # A name-based search can never claim exact-sequence directness.
    assert evidence.directness == Directness.INDIRECT


async def test_literature_check_reports_absence_when_no_hits(monkeypatch):
    async def fake_search(self, query, page_size=5):
        return ToolResult(
            provider="europe_pmc",
            operation="search",
            status=ToolStatus.OK,
            latency_ms=10.0,
            data={"hitCount": 0, "resultList": {"result": []}},
        )

    monkeypatch.setattr(EuropePmcClient, "search", fake_search)

    update = await literature_check(_state_with_name())

    evidence = update["evidence"][0]
    assert evidence.evidence_type == EvidenceType.ABSENCE_OF_EVIDENCE


async def test_literature_check_skipped_without_protein_name_does_not_call_api():
    calls = []

    async def fake_search(self, query, page_size=5):
        calls.append(query)
        raise AssertionError("Europe PMC should not be called without a protein name")

    state = InvestigationState(raw_sequence="MKV")
    update = await literature_check(state)

    assert calls == []
    assert update["tool_results"][-1].status == ToolStatus.SKIPPED
