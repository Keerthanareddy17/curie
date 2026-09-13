"""Offline-safe tests for agent nodes that don't require network access."""

from curie.agent.nodes.epitope_evidence import epitope_evidence
from curie.agent.nodes.literature_check import literature_check
from curie.agent.nodes.research_planner import research_planner
from curie.agent.nodes.sequence_intake import sequence_intake
from curie.agent.state import InvestigationState
from curie.shared.models import IdentityStatus, InvestigationStatus, SequenceType, ToolStatus
from tests.fixtures.sample_sequences import SARS_COV_2_SPIKE


def test_sequence_intake_classifies_protein_input():
    state = InvestigationState(raw_sequence=SARS_COV_2_SPIKE.sequence)
    update = sequence_intake(state)

    assert update["sequence_type"] == SequenceType.PROTEIN
    assert update["translated_sequence"] is None
    assert update["normalized_sequence"] == SARS_COV_2_SPIKE.sequence
    assert update["errors"] == []
    assert update["trace"][0].node == "sequence_intake"


def test_sequence_intake_translates_nucleotide_input():
    dna = "ATGGGCCGCTGA"  # M G R (stop)
    state = InvestigationState(raw_sequence=dna)
    update = sequence_intake(state)

    assert update["sequence_type"] == SequenceType.NUCLEOTIDE
    assert update["translated_sequence"] == "MGR"


def test_sequence_intake_flags_empty_result_as_error():
    state = InvestigationState(raw_sequence=">header only\n123456")
    update = sequence_intake(state)

    assert update["errors"], "expected an error when no valid residues remain"
    assert update["trace"][0].status == "error"


async def test_research_planner_allows_structure_within_limit(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    state = InvestigationState(raw_sequence="X", normalized_sequence="M" * 100)
    update = await research_planner(state)

    plan = update["research_plan"]
    assert plan.structure_allowed is True
    assert plan.needs_identity is True  # no accession_hint supplied
    assert update["status"] == InvestigationStatus.COLLECTING


async def test_research_planner_disallows_structure_over_limit(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    state = InvestigationState(raw_sequence="X", normalized_sequence="M" * 500)
    update = await research_planner(state)

    assert update["research_plan"].structure_allowed is False


async def test_research_planner_needs_identity_false_when_hint_given(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    state = InvestigationState(raw_sequence="X", normalized_sequence="M" * 10, accession_hint="P0DTC2")
    update = await research_planner(state)

    assert update["research_plan"].needs_identity is False


async def test_epitope_evidence_skips_without_resolved_identity():
    state = InvestigationState(
        raw_sequence=SARS_COV_2_SPIKE.sequence, identity_status=IdentityStatus.UNRESOLVED
    )
    update = await epitope_evidence(state)

    result = update["tool_results"][-1]
    assert result.status == ToolStatus.SKIPPED
    assert result.provider == "iedb"
    evidence = update["evidence"][-1]
    assert evidence.evidence_type.value == "absence_of_evidence"


async def test_literature_check_skips_without_protein_name():
    state = InvestigationState(raw_sequence=SARS_COV_2_SPIKE.sequence)
    assert state.protein_name is None

    update = await literature_check(state)

    result = update["tool_results"][-1]
    assert result.status == ToolStatus.SKIPPED
    assert result.provider == "europe_pmc"
