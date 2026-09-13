from curie.agent.nodes.epitope_evidence import epitope_evidence
from curie.agent.state import InvestigationState
from curie.shared.models import (
    CandidateProtein,
    EvidenceLevel,
    EvidenceType,
    IdentityStatus,
    ToolResult,
    ToolStatus,
)
from curie.tools.iedb import IedbClient
from tests.fixtures.mock_responses import MOCK_IEDB_EPITOPES


def _resolved_state(**overrides) -> InvestigationState:
    defaults = dict(
        raw_sequence="MKV",
        identity_status=IdentityStatus.RESOLVED_HINT,
        candidate_proteins=[
            CandidateProtein(accession="P0DTC2", name="Spike glycoprotein", match_type="accession_hint")
        ],
    )
    defaults.update(overrides)
    return InvestigationState(**defaults)


async def test_epitope_evidence_normalizes_curated_records(monkeypatch):
    async def fake_search(self, accession, limit=20):
        return ToolResult(
            provider="iedb",
            operation="search_epitopes_by_source_accession",
            status=ToolStatus.OK,
            latency_ms=10.0,
            data=MOCK_IEDB_EPITOPES,
        )

    monkeypatch.setattr(IedbClient, "search_epitopes_by_source_accession", fake_search)

    update = await epitope_evidence(_resolved_state())

    evidence = update["evidence"][-1]
    assert evidence.evidence_type == EvidenceType.CURATED_EPITOPE
    assert evidence.evidence_level == EvidenceLevel.CURATED
    assert evidence.metadata["epitope_count"] == len(MOCK_IEDB_EPITOPES)


async def test_epitope_evidence_reports_absence_when_iedb_returns_empty(monkeypatch):
    async def fake_search(self, accession, limit=20):
        return ToolResult(
            provider="iedb",
            operation="search_epitopes_by_source_accession",
            status=ToolStatus.OK,
            latency_ms=10.0,
            data=[],
        )

    monkeypatch.setattr(IedbClient, "search_epitopes_by_source_accession", fake_search)

    update = await epitope_evidence(_resolved_state())

    evidence = update["evidence"][-1]
    assert evidence.evidence_type == EvidenceType.ABSENCE_OF_EVIDENCE
    assert "no direct curated evidence found" in evidence.claim.lower()


async def test_epitope_evidence_never_calls_iedb_when_unresolved():
    calls = []

    async def fake_search(self, accession, limit=20):
        calls.append(accession)
        raise AssertionError("IEDB should not be called without resolved identity")

    state = InvestigationState(raw_sequence="MKV", identity_status=IdentityStatus.UNRESOLVED)
    update = await epitope_evidence(state)

    assert calls == []
    assert update["tool_results"][-1].status == ToolStatus.SKIPPED
