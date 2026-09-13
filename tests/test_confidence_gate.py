from curie.agent.nodes.confidence_gate import confidence_gate
from curie.agent.state import InvestigationState
from curie.shared.models import EvidenceConflict, IdentityStatus, InvestigationStatus


def test_gate_fails_when_no_normalized_sequence():
    state = InvestigationState(raw_sequence="123", normalized_sequence="")
    update = confidence_gate(state)
    assert update["status"] == InvestigationStatus.FAILED


def test_gate_flags_conflicting_when_unresolved_conflict_present():
    state = InvestigationState(
        raw_sequence="MKV",
        normalized_sequence="MKV",
        evidence_score=0.9,
        conflicts=[
            EvidenceConflict(
                claim="x", evidence_a="a", evidence_b="b", conflict_type="t", severity="high", resolved=False
            )
        ],
    )
    update = confidence_gate(state)
    assert update["status"] == InvestigationStatus.CONFLICTING


def test_gate_ignores_resolved_conflicts():
    state = InvestigationState(
        raw_sequence="MKV",
        normalized_sequence="MKV",
        identity_status=IdentityStatus.RESOLVED_HINT,
        evidence_score=0.9,
        conflicts=[
            EvidenceConflict(
                claim="x", evidence_a="a", evidence_b="b", conflict_type="t", severity="low", resolved=True
            )
        ],
    )
    update = confidence_gate(state)
    assert update["status"] == InvestigationStatus.SUPPORTED


def test_gate_caps_unresolved_identity_below_supported():
    state = InvestigationState(
        raw_sequence="MKV",
        normalized_sequence="MKV",
        identity_status=IdentityStatus.UNRESOLVED,
        evidence_score=0.95,
    )
    update = confidence_gate(state)
    assert update["status"] == InvestigationStatus.PARTIALLY_SUPPORTED


def test_gate_abstains_when_evidence_score_low():
    state = InvestigationState(
        raw_sequence="MKV",
        normalized_sequence="MKV",
        identity_status=IdentityStatus.UNRESOLVED,
        evidence_score=0.1,
    )
    update = confidence_gate(state)
    assert update["status"] == InvestigationStatus.INSUFFICIENT_EVIDENCE


def test_gate_supported_requires_resolved_identity_and_high_score():
    state = InvestigationState(
        raw_sequence="MKV",
        normalized_sequence="MKV",
        identity_status=IdentityStatus.RESOLVED_HINT,
        evidence_score=0.8,
    )
    update = confidence_gate(state)
    assert update["status"] == InvestigationStatus.SUPPORTED
