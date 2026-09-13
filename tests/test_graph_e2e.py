"""Deterministic, fully offline end-to-end graph test.

Monkeypatches all four tool clients so the real compiled LangGraph runs
start-to-finish against controlled fixture data — no network access, fully
reproducible. This is the "at least ONE deterministic end-to-end graph test
using controlled fixtures" the project spec requires; it exercises graph
routing, concurrent branch execution, evidence normalization, adjudication,
the confidence gate, and dossier generation together, as opposed to the
per-node unit tests elsewhere in this directory.
"""

from __future__ import annotations

from curie.agent.graph import run_investigation
from curie.shared.models import InvestigationStatus, ToolResult, ToolStatus
from curie.tools.esm_atlas import EsmAtlasClient
from curie.tools.europe_pmc import EuropePmcClient
from curie.tools.iedb import IedbClient
from curie.tools.uniprot import UniProtClient
from tests.fixtures.mock_responses import (
    MOCK_ESM_ATLAS_PDB,
    MOCK_EUROPE_PMC_SEARCH,
    MOCK_IEDB_EPITOPES,
    MOCK_UNIPROT_ENTRY,
)


def _patch_all_tools_success(monkeypatch):
    # Force the deterministic (no-Gemini) path regardless of whether a real
    # GEMINI_API_KEY happens to be configured in this environment's .env —
    # this test's whole point is to be reproducible without any live
    # dependency. Gemini's own success/fallback paths get their own
    # dedicated, explicitly-mocked tests (tests/test_research_planner_gemini.py,
    # tests/test_gemini_synthesis.py).
    monkeypatch.setenv("GEMINI_API_KEY", "")

    async def fake_get_entry(self, accession):
        return ToolResult(
            provider="uniprot", operation="get_entry", status=ToolStatus.OK,
            latency_ms=1.0, data=MOCK_UNIPROT_ENTRY,
        )

    async def fake_fold(self, sequence):
        return ToolResult(
            provider="esm_atlas", operation="fold_sequence", status=ToolStatus.OK,
            latency_ms=1.0, data=MOCK_ESM_ATLAS_PDB,
        )

    async def fake_iedb_search(self, accession, limit=20):
        return ToolResult(
            provider="iedb", operation="search_epitopes_by_source_accession",
            status=ToolStatus.OK, latency_ms=1.0, data=MOCK_IEDB_EPITOPES,
        )

    async def fake_pmc_search(self, query, page_size=5):
        return ToolResult(
            provider="europe_pmc", operation="search", status=ToolStatus.OK,
            latency_ms=1.0, data=MOCK_EUROPE_PMC_SEARCH,
        )

    monkeypatch.setattr(UniProtClient, "get_entry", fake_get_entry)
    monkeypatch.setattr(EsmAtlasClient, "fold_sequence", fake_fold)
    monkeypatch.setattr(IedbClient, "search_epitopes_by_source_accession", fake_iedb_search)
    monkeypatch.setattr(EuropePmcClient, "search", fake_pmc_search)


async def test_full_graph_end_to_end_with_all_sources_agreeing(monkeypatch):
    _patch_all_tools_success(monkeypatch)

    state = await run_investigation("MKVFLVLLPLVSSQCVNLTT", accession_hint="P0DTC2")

    # Routing: every node ran exactly once (no double-fire from the fan-in join).
    node_names = [t.node for t in state.trace]
    expected_nodes = {
        "sequence_intake", "research_planner", "identity_resolution",
        "structure_prediction", "epitope_evidence", "literature_check",
        "evidence_normalization", "evidence_adjudication", "confidence_gate",
        "gemini_synthesis", "dossier_generation",
    }
    assert set(node_names) == expected_nodes
    for name in expected_nodes:
        assert node_names.count(name) == 1, f"{name} ran {node_names.count(name)} times"

    # Tool calls: all four real integrations were exercised, all succeeded.
    # gemini_synthesis always records its own ToolResult even when skipped
    # (no key configured here, by design — see _patch_all_tools_success).
    providers = {r.provider for r in state.tool_results}
    assert providers == {"uniprot", "esm_atlas", "iedb", "europe_pmc", "gemini"}
    gemini_result = next(r for r in state.tool_results if r.provider == "gemini")
    assert gemini_result.status == ToolStatus.SKIPPED
    assert all(r.status == ToolStatus.OK for r in state.tool_results if r.provider != "gemini")

    # Evidence normalized, adjudicated, no conflicts (fixtures agree), abstention gate says SUPPORTED.
    assert len(state.evidence) >= 4
    assert state.conflicts == []
    assert state.evidence_score == 1.0
    assert state.status == InvestigationStatus.SUPPORTED

    # Dossier assembled from that same structured state.
    assert state.dossier is not None
    assert state.dossier.final_status == InvestigationStatus.SUPPORTED
    assert state.dossier.evidence_score == 1.0


async def test_full_graph_end_to_end_abstains_without_identity(monkeypatch):
    _patch_all_tools_success(monkeypatch)

    state = await run_investigation("MKVFLVLLPLVSSQCVNLTT", accession_hint=None)

    # No accession hint -> uniprot/iedb/europe_pmc never even attempted for identity-gated steps.
    providers = {r.provider for r in state.tool_results}
    assert providers == {"esm_atlas", "iedb", "europe_pmc", "gemini"}
    iedb_result = next(r for r in state.tool_results if r.provider == "iedb")
    pmc_result = next(r for r in state.tool_results if r.provider == "europe_pmc")
    assert iedb_result.status == ToolStatus.SKIPPED
    assert pmc_result.status == ToolStatus.SKIPPED

    # Abstention, not a hallucinated conclusion.
    assert state.status in (
        InvestigationStatus.INSUFFICIENT_EVIDENCE,
        InvestigationStatus.PARTIALLY_SUPPORTED,
    )
    assert state.status != InvestigationStatus.SUPPORTED
    assert "UNRESOLVED" in state.dossier.identity_result
