from curie.agent.nodes.identity_resolution import identity_resolution
from curie.agent.state import InvestigationState
from curie.shared.models import EvidenceType, IdentityStatus, ToolResult, ToolStatus
from curie.tools.uniprot import UniProtClient
from tests.fixtures.mock_responses import MOCK_UNIPROT_ENTRY


async def test_identity_unresolved_without_accession_hint():
    state = InvestigationState(raw_sequence="MKV", accession_hint=None)
    update = await identity_resolution(state)

    assert update["identity_status"] == IdentityStatus.UNRESOLVED
    assert update["evidence"][-1].evidence_type == EvidenceType.ABSENCE_OF_EVIDENCE
    assert "tool_results" not in update  # no UniProt call was made at all


async def test_identity_resolves_with_valid_accession_hint(monkeypatch):
    async def fake_get_entry(self, accession):
        return ToolResult(
            provider="uniprot",
            operation="get_entry",
            status=ToolStatus.OK,
            latency_ms=10.0,
            data=MOCK_UNIPROT_ENTRY,
        )

    monkeypatch.setattr(UniProtClient, "get_entry", fake_get_entry)

    state = InvestigationState(raw_sequence="MKV", accession_hint="P0DTC2")
    update = await identity_resolution(state)

    assert update["identity_status"] == IdentityStatus.RESOLVED_HINT
    assert update["protein_name"] == "Spike glycoprotein"
    assert update["candidate_proteins"][0].accession == "P0DTC2"
    assert update["candidate_proteins"][0].match_type == "accession_hint"


async def test_identity_stays_unresolved_when_uniprot_lookup_fails(monkeypatch):
    async def fake_get_entry(self, accession):
        return ToolResult(
            provider="uniprot",
            operation="get_entry",
            status=ToolStatus.ERROR,
            latency_ms=10.0,
            error="404 not found",
        )

    monkeypatch.setattr(UniProtClient, "get_entry", fake_get_entry)

    state = InvestigationState(raw_sequence="MKV", accession_hint="BOGUS999")
    update = await identity_resolution(state)

    assert update["identity_status"] == IdentityStatus.UNRESOLVED
    assert update["protein_name"] is None
    # No candidate should ever be fabricated from a failed lookup.
    assert update["candidate_proteins"] == []
