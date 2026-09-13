from curie.agent.nodes.dossier_generation import dossier_generation
from curie.agent.state import InvestigationState
from curie.shared.models import (
    CandidateProtein,
    Directness,
    EvidenceLevel,
    EvidenceRecord,
    EvidenceType,
    IdentityStatus,
    InvestigationStatus,
    SequenceType,
)


def test_dossier_reflects_resolved_identity_and_evidence_groups():
    state = InvestigationState(
        raw_sequence="MKV",
        normalized_sequence="MKV",
        sequence_type=SequenceType.PROTEIN,
        identity_status=IdentityStatus.RESOLVED_HINT,
        candidate_proteins=[
            CandidateProtein(accession="P0DTC2", name="Spike glycoprotein", match_type="accession_hint")
        ],
        evidence=[
            EvidenceRecord(
                source="uniprot",
                source_type="database",
                claim="x",
                evidence_type=EvidenceType.CURATED_ANNOTATION,
                evidence_level=EvidenceLevel.CURATED,
                directness=Directness.DIRECT,
            ),
            EvidenceRecord(
                source="esm_atlas",
                source_type="prediction",
                claim="y",
                evidence_type=EvidenceType.PREDICTED_STRUCTURE,
                evidence_level=EvidenceLevel.PREDICTED,
                directness=Directness.DIRECT,
                confidence=95.0,
            ),
        ],
        evidence_score=0.9,
        status=InvestigationStatus.SUPPORTED,
    )

    update = dossier_generation(state)
    dossier = update["dossier"]

    assert dossier.investigation_id == state.run_id
    assert "P0DTC2" in dossier.identity_result
    assert len(dossier.identity_evidence) == 1
    assert len(dossier.structural_evidence) == 1
    assert dossier.final_status == InvestigationStatus.SUPPORTED
    assert any("wet-lab" in limitation for limitation in dossier.limitations)


def test_dossier_states_unresolved_identity_honestly():
    state = InvestigationState(
        raw_sequence="MKV",
        normalized_sequence="MKV",
        identity_status=IdentityStatus.UNRESOLVED,
        status=InvestigationStatus.INSUFFICIENT_EVIDENCE,
    )

    update = dossier_generation(state)
    dossier = update["dossier"]

    assert "UNRESOLVED" in dossier.identity_result
    assert any("sequence-similarity search" in q for q in dossier.next_research_questions)


def test_dossier_never_produces_a_clinical_recommendation():
    state = InvestigationState(raw_sequence="MKV", normalized_sequence="MKV")
    update = dossier_generation(state)
    dossier = update["dossier"]

    full_text = " ".join(dossier.limitations).lower()
    assert "clinical" in full_text or "therapeutic" in full_text
