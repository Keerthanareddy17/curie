"""Network smoke test: runs the real graph against real ESM Atlas / UniProt / IEDB /
Europe PMC. Marked `network` so it can be deselected (`pytest -m "not network"`) in
offline environments; not mocked, because the whole point of this phase is that
these tool calls are real. For a fully offline, deterministic, mocked run of the
same graph shape, see tests/test_graph_e2e.py.
"""

import pytest

from curie.agent.graph import run_investigation
from curie.shared.models import IdentityStatus, InvestigationStatus, ToolStatus
from tests.fixtures.sample_sequences import SHORT_SYNTHETIC_PROTEIN

pytestmark = pytest.mark.network


async def test_full_graph_runs_end_to_end_without_accession_hint():
    state = await run_investigation(SHORT_SYNTHETIC_PROTEIN.sequence)

    assert state.sequence_type.value == "protein"
    assert state.identity_status == IdentityStatus.UNRESOLVED
    assert state.dossier is not None
    # esm_atlas should have actually been called; iedb/europe_pmc are expected
    # SKIPPED since no accession_hint was supplied (no resolved identity).
    providers_called = {r.provider for r in state.tool_results}
    assert "esm_atlas" in providers_called
    assert state.status in (
        InvestigationStatus.INSUFFICIENT_EVIDENCE,
        InvestigationStatus.PARTIALLY_SUPPORTED,
    )


async def test_full_graph_runs_end_to_end_with_accession_hint():
    state = await run_investigation(
        "SIIAYTMSLGAENSVAYSNNSIAIPTNFTISVTTEILPVSMTKTSVDCTMYICGDSTECSNLLLQYGSFCTQLNRALTGIA",
        accession_hint="P0DTC2",
    )

    assert state.dossier is not None
    esm_result = next(r for r in state.tool_results if r.provider == "esm_atlas")
    uniprot_result = next(r for r in state.tool_results if r.provider == "uniprot")
    iedb_result = next(r for r in state.tool_results if r.provider == "iedb")
    europe_pmc_result = next(r for r in state.tool_results if r.provider == "europe_pmc")

    # These are real network calls; assert they completed with *some* verdict
    # rather than requiring OK, since third-party availability isn't guaranteed.
    for result in (esm_result, uniprot_result, iedb_result, europe_pmc_result):
        assert result.status in (
            ToolStatus.OK,
            ToolStatus.ERROR,
            ToolStatus.TIMEOUT,
            ToolStatus.SKIPPED,
        )

    if uniprot_result.status == ToolStatus.OK:
        assert state.identity_status == IdentityStatus.RESOLVED_HINT
        assert state.protein_name is not None

    assert state.evidence_score is not None
    assert len(state.trace) >= 9  # one per node in the graph
