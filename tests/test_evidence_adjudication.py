from curie.agent.nodes.evidence_adjudication import evidence_adjudication
from curie.agent.state import InvestigationState
from curie.shared.models import (
    CandidateProtein,
    Directness,
    EvidenceLevel,
    EvidenceRecord,
    EvidenceType,
    IdentityStatus,
    ToolResult,
    ToolStatus,
)


def _evidence(source: str, claim: str) -> EvidenceRecord:
    return EvidenceRecord(
        source=source,
        source_type="database",
        claim=claim,
        evidence_type=EvidenceType.CURATED_ANNOTATION,
        evidence_level=EvidenceLevel.CURATED,
        directness=Directness.DIRECT,
    )


def test_adjudication_detects_conflict_between_disagreeing_sources():
    uniprot_result = ToolResult(
        provider="uniprot",
        operation="get_entry",
        status=ToolStatus.OK,
        latency_ms=1.0,
        data={"results": [{"proteinDescription": {"recommendedName": {"fullName": {"value": "Hemagglutinin"}}}}]},
    )
    iedb_result = ToolResult(
        provider="iedb",
        operation="search",
        status=ToolStatus.OK,
        latency_ms=1.0,
        data=[{"parent_source_antigen_names": ["Spike glycoprotein (UniProt:P0DTC2)"]}],
    )

    state = InvestigationState(
        raw_sequence="MKV",
        identity_status=IdentityStatus.RESOLVED_HINT,
        candidate_proteins=[CandidateProtein(accession="P0DTC2", match_type="accession_hint")],
        tool_results=[uniprot_result, iedb_result],
        evidence=[_evidence("uniprot", "uniprot says Hemagglutinin"), _evidence("iedb", "iedb says Spike")],
    )

    update = evidence_adjudication(state)

    assert len(update["conflicts"]) >= 1
    assert update["evidence_score"] < 1.0


def test_adjudication_no_conflict_when_sources_agree():
    uniprot_result = ToolResult(
        provider="uniprot",
        operation="get_entry",
        status=ToolStatus.OK,
        latency_ms=1.0,
        data={"results": [{"proteinDescription": {"recommendedName": {"fullName": {"value": "Spike glycoprotein"}}}}]},
    )
    iedb_result = ToolResult(
        provider="iedb",
        operation="search",
        status=ToolStatus.OK,
        latency_ms=1.0,
        data=[{"parent_source_antigen_names": ["Spike glycoprotein (UniProt:P0DTC2)"]}],
    )
    esm_result = ToolResult(
        provider="esm_atlas", operation="fold_sequence", status=ToolStatus.OK, latency_ms=1.0, data="ATOM..."
    )

    state = InvestigationState(
        raw_sequence="MKV",
        identity_status=IdentityStatus.RESOLVED_HINT,
        candidate_proteins=[CandidateProtein(accession="P0DTC2", match_type="accession_hint")],
        tool_results=[uniprot_result, iedb_result, esm_result],
        evidence=[_evidence("uniprot", "x"), _evidence("iedb", "y"), _evidence("esm_atlas", "z")],
    )

    update = evidence_adjudication(state)

    assert update["conflicts"] == []
    assert update["evidence_score"] == 1.0


def test_adjudication_missing_evidence_lists_skipped_and_failed_calls():
    state = InvestigationState(
        raw_sequence="MKV",
        identity_status=IdentityStatus.UNRESOLVED,
        tool_results=[
            ToolResult(
                provider="iedb",
                operation="search",
                status=ToolStatus.SKIPPED,
                latency_ms=0.0,
                error="identity unresolved",
            )
        ],
    )

    update = evidence_adjudication(state)

    assert any("iedb" in m for m in update["missing_evidence"])
    assert any("identity is unresolved" in m for m in update["missing_evidence"])
