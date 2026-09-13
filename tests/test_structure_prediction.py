from curie.agent.nodes.structure_prediction import structure_prediction
from curie.agent.state import InvestigationState
from curie.shared.models import EvidenceType, ToolStatus
from curie.tools.esm_atlas import EsmAtlasClient, MAX_SEQUENCE_LENGTH, mean_plddt
from tests.fixtures.mock_responses import MOCK_ESM_ATLAS_PDB


def test_mean_plddt_parses_b_factor_column():
    confidence = mean_plddt(MOCK_ESM_ATLAS_PDB)
    assert confidence is not None
    assert 90.0 < confidence < 93.0  # fixture's three ATOM lines average ~91.2


def test_mean_plddt_returns_none_for_no_atom_lines():
    assert mean_plddt("HEADER only\nEND\n") is None


def test_mean_plddt_rescales_a_fractional_0_to_1_b_factor_scale():
    """Regression test: found live during Phase 4 UI verification that the
    real api.esmatlas.com endpoint emits B-factors as a 0.0-1.0 fraction, not
    the conventional 0-100 pLDDT percentage — it was rendering as a
    misleadingly tiny "0.2 pLDDT" in the UI. mean_plddt must detect and
    rescale this, not just average whatever raw column values it finds."""
    fractional_pdb = (
        "HEADER    FRACTIONAL SCALE FIXTURE\n"
        "ATOM      1  N   MET A   1      11.104  13.207   2.100  1.00  0.29           N\n"
        "ATOM      2  CA  MET A   1      12.560  13.207   2.100  1.00  0.32           C\n"
        "ATOM      3  C   MET A   1      13.100  14.600   2.100  1.00  0.30           C\n"
        "END\n"
    )
    confidence = mean_plddt(fractional_pdb)
    assert confidence is not None
    assert 29.0 < confidence < 32.0  # (29+32+30)/3 rescaled to 0-100, not 0.29-0.32


async def test_structure_prediction_skips_sequences_over_limit():
    state = InvestigationState(raw_sequence="X", normalized_sequence="M" * (MAX_SEQUENCE_LENGTH + 1))
    update = await structure_prediction(state)

    result = update["tool_results"][-1]
    assert result.status == ToolStatus.SKIPPED
    assert "exceeds supported fold length" in result.error
    assert update["evidence"][-1].evidence_type == EvidenceType.ABSENCE_OF_EVIDENCE


async def test_structure_prediction_skips_empty_sequence():
    state = InvestigationState(raw_sequence="X", normalized_sequence="")
    update = await structure_prediction(state)

    assert update["tool_results"][-1].status == ToolStatus.SKIPPED


async def test_structure_prediction_calls_esm_atlas_and_records_confidence(monkeypatch):
    async def fake_fold_sequence(self, sequence):
        from curie.shared.models import ToolResult

        return ToolResult(
            provider="esm_atlas",
            operation="fold_sequence",
            status=ToolStatus.OK,
            latency_ms=42.0,
            data=MOCK_ESM_ATLAS_PDB,
        )

    monkeypatch.setattr(EsmAtlasClient, "fold_sequence", fake_fold_sequence)

    state = InvestigationState(raw_sequence="X", normalized_sequence="MKV")
    update = await structure_prediction(state)

    evidence = update["evidence"][-1]
    assert evidence.evidence_type == EvidenceType.PREDICTED_STRUCTURE
    assert evidence.confidence is not None
    assert update["tool_results"][-1].status == ToolStatus.OK
