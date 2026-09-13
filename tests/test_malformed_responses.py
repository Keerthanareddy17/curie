"""Regression tests for a bug found while designing Phase 3's fault-injection
scenarios: a 200 OK response whose body isn't the expected dict shape (e.g. a
bare list, a string, or None) used to crash `identity_resolution` and
`literature_check` with an uncaught AttributeError from `.get()`, taking the
whole graph run down instead of degrading gracefully like every other failure
mode. Fixed in curie/agent/nodes/identity_resolution.py and literature_check.py.
"""

from curie.agent.nodes.identity_resolution import identity_resolution
from curie.agent.nodes.literature_check import literature_check
from curie.agent.state import InvestigationState
from curie.shared.models import EvidenceType, IdentityStatus, ToolResult, ToolStatus
from curie.tools.europe_pmc import EuropePmcClient
from curie.tools.uniprot import UniProtClient


async def test_identity_resolution_survives_non_dict_uniprot_payload(monkeypatch):
    async def fake_get_entry(self, accession):
        return ToolResult(
            provider="uniprot", operation="get_entry", status=ToolStatus.OK,
            latency_ms=1.0, data=["unexpected", "list", "payload"],
        )

    monkeypatch.setattr(UniProtClient, "get_entry", fake_get_entry)

    state = InvestigationState(raw_sequence="MKV", accession_hint="P0DTC2")
    update = await identity_resolution(state)  # must not raise

    assert update["identity_status"] == IdentityStatus.UNRESOLVED
    assert update["candidate_proteins"] == []
    assert update["evidence"][0].evidence_type == EvidenceType.ABSENCE_OF_EVIDENCE
    assert update["trace"][0].status == "error"


async def test_identity_resolution_survives_null_uniprot_payload(monkeypatch):
    async def fake_get_entry(self, accession):
        return ToolResult(
            provider="uniprot", operation="get_entry", status=ToolStatus.OK,
            latency_ms=1.0, data=None,
        )

    monkeypatch.setattr(UniProtClient, "get_entry", fake_get_entry)

    state = InvestigationState(raw_sequence="MKV", accession_hint="P0DTC2")
    update = await identity_resolution(state)  # must not raise

    assert update["identity_status"] == IdentityStatus.UNRESOLVED


async def test_literature_check_survives_non_dict_europe_pmc_payload(monkeypatch):
    async def fake_search(self, query, page_size=5):
        return ToolResult(
            provider="europe_pmc", operation="search", status=ToolStatus.OK,
            latency_ms=1.0, data="not a dict at all",
        )

    monkeypatch.setattr(EuropePmcClient, "search", fake_search)

    state = InvestigationState(raw_sequence="MKV", protein_name="Spike glycoprotein")
    update = await literature_check(state)  # must not raise

    assert update["evidence"][0].evidence_type == EvidenceType.ABSENCE_OF_EVIDENCE
    assert update["trace"][0].status == "error"
