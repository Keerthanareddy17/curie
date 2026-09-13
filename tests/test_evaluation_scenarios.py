"""Regression tests wrapping curie/evaluation/scenarios/fault_scenarios.py in
pytest, plus a dedicated graph-routing-after-failure check. All fully offline
(every tool client is monkeypatched by ToolPatch) — no `network` marker needed.
"""

from __future__ import annotations

from curie.agent.graph import run_investigation
from curie.evaluation.fixtures.fault_adapters import ToolPatch, error_esm_failed
from curie.evaluation.scenarios.fault_scenarios import (
    RBD_SEQUENCE,
    scenario_a_esm_timeout,
    scenario_b_oversized_sequence,
    scenario_c_uniprot_no_match,
    scenario_d_conflicting_evidence,
    scenario_e_insufficient_evidence,
    scenario_f_malformed_response,
    scenario_g_homolog_literature,
    scenario_h_tool_unavailable,
)


async def test_scenario_a_esm_timeout_passes():
    result = await scenario_a_esm_timeout()
    assert result.passed, result.checks


async def test_scenario_b_oversized_sequence_passes():
    result = await scenario_b_oversized_sequence()
    assert result.passed, result.checks


async def test_scenario_c_uniprot_no_match_passes():
    result = await scenario_c_uniprot_no_match()
    assert result.passed, result.checks


async def test_scenario_d_conflicting_evidence_passes():
    result = await scenario_d_conflicting_evidence()
    assert result.passed, result.checks
    assert result.conflict_detected is True


async def test_scenario_e_insufficient_evidence_passes():
    result = await scenario_e_insufficient_evidence()
    assert result.passed, result.checks


async def test_scenario_f_malformed_response_passes():
    result = await scenario_f_malformed_response()
    assert result.passed, result.checks


async def test_scenario_g_homolog_literature_passes():
    result = await scenario_g_homolog_literature()
    assert result.passed, result.checks


async def test_scenario_h_tool_unavailable_passes():
    result = await scenario_h_tool_unavailable()
    assert result.passed, result.checks


async def test_no_scenario_crashes():
    """Every scenario must degrade gracefully — none may raise."""
    for scenario in (
        scenario_a_esm_timeout, scenario_b_oversized_sequence, scenario_c_uniprot_no_match,
        scenario_d_conflicting_evidence, scenario_e_insufficient_evidence,
        scenario_f_malformed_response, scenario_g_homolog_literature, scenario_h_tool_unavailable,
    ):
        result = await scenario()
        assert result.crashed is False, f"{result.scenario_id} crashed: {result.actual_behavior}"


async def test_graph_routing_continues_correctly_after_a_tool_failure(monkeypatch):
    """Explicit regression test for graph routing under failure: even when
    esm_atlas fails, every downstream node (including the fan-in join
    evidence_normalization) must still run exactly once — not zero times
    (graph got stuck) and not more than once (the fan-in bug this project's
    graph design specifically guards against with defer=True)."""
    monkeypatch.setenv("GEMINI_API_KEY", "")  # keep this test offline/deterministic
    with ToolPatch(esm_atlas=error_esm_failed):
        state = await run_investigation(RBD_SEQUENCE, accession_hint="P0DTC2")

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
    assert state.dossier is not None
