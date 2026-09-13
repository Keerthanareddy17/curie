from curie.shared.models import AgreementLevel, ToolResult, ToolStatus
from curie.tools.evidence_verification import (
    verify_identity_consistency,
    verify_structural_and_epitope_evidence_present,
)
from tests.fixtures.mock_responses import (
    MOCK_IEDB_EPITOPES,
    MOCK_UNIPROT_ENTRY,
    MOCK_UNIPROT_SEARCH,
)


def _ok_result(provider: str, operation: str, data) -> ToolResult:
    return ToolResult(provider=provider, operation=operation, status=ToolStatus.OK, latency_ms=1.0, data=data)


def _failed_result(provider: str, operation: str) -> ToolResult:
    return ToolResult(
        provider=provider, operation=operation, status=ToolStatus.ERROR, latency_ms=1.0, error="boom"
    )


def test_identity_consistency_agrees_when_names_overlap():
    uniprot_result = _ok_result("uniprot", "search", MOCK_UNIPROT_SEARCH)
    iedb_result = _ok_result("iedb", "search_epitopes_by_source_accession", MOCK_IEDB_EPITOPES)

    finding = verify_identity_consistency(uniprot_result, iedb_result)

    assert finding.agreement == AgreementLevel.AGREE
    assert "uniprot" in finding.supporting_sources
    assert "iedb" in finding.supporting_sources


def test_identity_consistency_conflicts_when_names_dont_overlap():
    uniprot_result = _ok_result(
        "uniprot",
        "search",
        {"results": [{"proteinDescription": {"recommendedName": {"fullName": {"value": "Hemagglutinin"}}}}]},
    )
    iedb_result = _ok_result("iedb", "search", MOCK_IEDB_EPITOPES)

    finding = verify_identity_consistency(uniprot_result, iedb_result)

    assert finding.agreement == AgreementLevel.CONFLICT


def test_identity_consistency_agrees_with_get_entry_shaped_uniprot_payload():
    """Regression test: identity_resolution.py calls UniProtClient.get_entry(),
    which returns a bare single-entry dict (MOCK_UNIPROT_ENTRY), not a search
    response wrapped in {"results": [...]} (MOCK_UNIPROT_SEARCH). Before the
    Phase 3 fix, `verify_identity_consistency` only ever looked for a
    "results" key, so it silently extracted zero names from every real
    get_entry response and always returned UNVERIFIABLE — found via
    fault-injection testing, not by inspection, and confirmed to have been
    true of every prior live run of the whole system."""
    uniprot_result = _ok_result("uniprot", "get_entry", MOCK_UNIPROT_ENTRY)
    iedb_result = _ok_result("iedb", "search_epitopes_by_source_accession", MOCK_IEDB_EPITOPES)

    finding = verify_identity_consistency(uniprot_result, iedb_result)

    assert finding.agreement == AgreementLevel.AGREE


def test_identity_consistency_conflicts_with_get_entry_shaped_uniprot_payload():
    uniprot_result = _ok_result(
        "uniprot", "get_entry",
        {"proteinDescription": {"recommendedName": {"fullName": {"value": "Hemagglutinin"}}}},
    )
    iedb_result = _ok_result("iedb", "search_epitopes_by_source_accession", MOCK_IEDB_EPITOPES)

    finding = verify_identity_consistency(uniprot_result, iedb_result)

    assert finding.agreement == AgreementLevel.CONFLICT


def test_identity_consistency_unverifiable_when_a_source_failed():
    uniprot_result = _failed_result("uniprot", "search")
    iedb_result = _ok_result("iedb", "search", MOCK_IEDB_EPITOPES)

    finding = verify_identity_consistency(uniprot_result, iedb_result)

    assert finding.agreement == AgreementLevel.UNVERIFIABLE


def test_structural_and_epitope_evidence_agree_when_both_present():
    esm_result = _ok_result("esm_atlas", "fold_sequence", "ATOM...")
    iedb_result = _ok_result("iedb", "search", MOCK_IEDB_EPITOPES)

    finding = verify_structural_and_epitope_evidence_present(esm_result, iedb_result)

    assert finding.agreement == AgreementLevel.AGREE


def test_structural_and_epitope_evidence_partial_when_one_missing():
    esm_result = _ok_result("esm_atlas", "fold_sequence", "ATOM...")
    iedb_result = _failed_result("iedb", "search")

    finding = verify_structural_and_epitope_evidence_present(esm_result, iedb_result)

    assert finding.agreement == AgreementLevel.PARTIAL
