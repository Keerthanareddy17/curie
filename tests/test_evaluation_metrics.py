"""Regression tests for curie/evaluation/metrics/metrics.py.

The live benchmark run happened to score 100% on every provenance/grounding/
unsupported-claim check (see curie/evaluation/results/latest.md) because the
6 real cases all have clean, well-formed evidence. That is not, by itself,
proof the *detectors* work — a check that always returns "valid" regardless
of input would also show 100%. The negative-case tests below deliberately
construct bad evidence/claims and assert the checks actually catch them.
"""

from __future__ import annotations

from curie.evaluation.metrics.metrics import (
    check_claim_grounding,
    check_end_to_end,
    check_provenance,
    check_sources,
    check_unsupported_claims,
    classify_cross_source_consistency,
    classify_identity,
)
from curie.evaluation.models import (
    BenchmarkCase,
    EvidenceExpectation,
    ExpectedIdentity,
    ExpectedOutcome,
    IdentityEvalClass,
)
from curie.agent.state import InvestigationState
from curie.shared.models import (
    AgreementLevel,
    Claim,
    Directness,
    EvidenceLevel,
    EvidenceRecord,
    EvidenceType,
    IdentityStatus,
    InvestigationStatus,
    ToolResult,
    ToolStatus,
)


def _case(accession_hint=None, identity_status="not_evaluated", final_behavior="not_evaluated", evidence_expectations=None):
    return BenchmarkCase(
        case_id="t",
        description="test",
        sequence="MKV",
        accession_hint=accession_hint,
        expected=ExpectedOutcome(
            identity=ExpectedIdentity(status=identity_status),
            evidence_expectations=evidence_expectations or [],
            final_behavior=final_behavior,
        ),
    )


# --- identity-hint exclusion (spec section 6, "no free information") -------


def test_identity_hint_case_is_always_classified_supplied_never_resolved():
    """Regardless of what identity_status the run actually produced, a case
    that supplied accession_hint must be SUPPLIED — never counted as
    RESOLVED/UNRESOLVED identity-accuracy signal."""
    case = _case(accession_hint="P0DTC2")
    state_resolved = InvestigationState(raw_sequence="MKV", identity_status=IdentityStatus.RESOLVED_HINT)
    state_unresolved = InvestigationState(raw_sequence="MKV", identity_status=IdentityStatus.UNRESOLVED)

    assert classify_identity(case, state_resolved) == IdentityEvalClass.SUPPLIED
    assert classify_identity(case, state_unresolved) == IdentityEvalClass.SUPPLIED


def test_no_hint_case_with_expectation_classified_unresolved():
    case = _case(accession_hint=None, identity_status="unresolved")
    state = InvestigationState(raw_sequence="MKV", identity_status=IdentityStatus.UNRESOLVED)
    assert classify_identity(case, state) == IdentityEvalClass.UNRESOLVED


def test_case_without_identity_expectation_is_not_evaluated():
    case = _case(accession_hint=None, identity_status="not_evaluated")
    state = InvestigationState(raw_sequence="MKV")
    assert classify_identity(case, state) == IdentityEvalClass.NOT_EVALUATED


# --- source retrieval (Metric 1) --------------------------------------------


def test_check_sources_distinguishes_pass_fail_skip_not_evaluated():
    case = _case(evidence_expectations=[
        EvidenceExpectation(source="uniprot", should_be_called=True, expect_status="ok"),
        EvidenceExpectation(source="iedb", should_be_called=True, expect_status="ok"),
        EvidenceExpectation(source="europe_pmc", should_be_called=False, expect_status="skipped"),
        EvidenceExpectation(source="esm_atlas", should_be_called=True, expect_status=None),
    ])
    state = InvestigationState(
        raw_sequence="MKV",
        tool_results=[
            ToolResult(provider="uniprot", operation="get_entry", status=ToolStatus.OK, latency_ms=1.0),
            ToolResult(provider="iedb", operation="search", status=ToolStatus.ERROR, latency_ms=1.0, error="boom"),
            ToolResult(provider="europe_pmc", operation="search", status=ToolStatus.SKIPPED, latency_ms=0.0),
        ],
    )
    results = {r.source: r.outcome for r in check_sources(case, state)}
    assert results["uniprot"] == "PASS"
    assert results["iedb"] == "FAILED"
    assert results["europe_pmc"] == "SKIPPED_CORRECTLY"
    assert results["esm_atlas"] == "NOT_EVALUATED"


# --- provenance (Metric 2) — negative-case proof ----------------------------


def test_provenance_rejects_evidence_with_no_backing_tool_result():
    """A record claiming to be from 'iedb' when no successful iedb ToolResult
    exists must fail provenance — this is the check that would catch a
    citation invented without a real call behind it."""
    state = InvestigationState(
        raw_sequence="MKV",
        tool_results=[],  # no tool was ever called
        evidence=[
            EvidenceRecord(
                source="iedb", source_type="database", identifier="P0DTC2",
                claim="fabricated claim with no backing call",
                evidence_type=EvidenceType.CURATED_EPITOPE,
                evidence_level=EvidenceLevel.CURATED, directness=Directness.DIRECT,
            )
        ],
    )
    results = check_provenance(state)
    assert len(results) == 1
    assert results[0].valid is False
    assert any("no successful ToolResult" in r for r in results[0].reasons)


def test_provenance_rejects_literature_identifier_not_in_raw_response():
    backing = ToolResult(
        provider="europe_pmc", operation="search", status=ToolStatus.OK, latency_ms=1.0,
        data={"resultList": {"result": [{"id": "111"}]}},
    )
    state = InvestigationState(
        raw_sequence="MKV",
        tool_results=[backing],
        evidence=[
            EvidenceRecord(
                source="europe_pmc", source_type="literature", identifier="999999",  # not in raw response
                claim="invented pmid",
                evidence_type=EvidenceType.LITERATURE,
                evidence_level=EvidenceLevel.CURATED, directness=Directness.INDIRECT,
            )
        ],
    )
    results = check_provenance(state)
    assert results[0].valid is False
    assert any("not found in the backing call" in r for r in results[0].reasons)


def test_provenance_accepts_well_formed_evidence():
    backing = ToolResult(provider="uniprot", operation="get_entry", status=ToolStatus.OK, latency_ms=1.0, data={})
    state = InvestigationState(
        raw_sequence="MKV",
        tool_results=[backing],
        evidence=[
            EvidenceRecord(
                source="uniprot", source_type="database", identifier="P0DTC2",
                claim="fine", evidence_type=EvidenceType.CURATED_ANNOTATION,
                evidence_level=EvidenceLevel.CURATED, directness=Directness.DIRECT,
            )
        ],
    )
    assert check_provenance(state)[0].valid is True


def test_provenance_skips_absence_of_evidence_records():
    state = InvestigationState(
        raw_sequence="MKV",
        evidence=[
            EvidenceRecord(
                source="iedb", source_type="database", claim="nothing found",
                evidence_type=EvidenceType.ABSENCE_OF_EVIDENCE,
                evidence_level=EvidenceLevel.NONE, directness=Directness.DIRECT,
            )
        ],
    )
    assert check_provenance(state) == []


# --- claim grounding / unsupported claims (Metrics 3, 9) — negative proof ---


def test_claim_citing_nonexistent_evidence_id_is_not_grounded_and_unsupported():
    """The literal 'citation-shaped hallucination' case: a claim that cites an
    evidence_id which doesn't exist in state.evidence at all."""
    state = InvestigationState(
        raw_sequence="MKV",
        claims=[
            Claim(
                statement="fabricated",
                supporting_evidence_ids=["does-not-exist"],
                agreement=AgreementLevel.AGREE,
            )
        ],
    )
    grounding = check_claim_grounding(state)
    assert grounding[0].grounded is False
    assert "nonexistent" in grounding[0].reason

    unsupported = check_unsupported_claims(state)
    assert unsupported[0].unsupported is True


def test_claim_agree_with_no_cited_evidence_is_unsupported():
    state = InvestigationState(
        raw_sequence="MKV",
        claims=[Claim(statement="agrees but cites nothing", agreement=AgreementLevel.AGREE)],
    )
    assert check_claim_grounding(state)[0].grounded is False
    assert check_unsupported_claims(state)[0].unsupported is True


def test_unverifiable_claim_with_no_evidence_is_vacuously_grounded():
    """UNVERIFIABLE claims assert nothing beyond 'insufficient data' — citing
    no evidence is honest, not a hallucination."""
    state = InvestigationState(
        raw_sequence="MKV",
        claims=[Claim(statement="cannot verify", agreement=AgreementLevel.UNVERIFIABLE)],
    )
    assert check_claim_grounding(state)[0].grounded is True
    assert check_unsupported_claims(state)[0].unsupported is False


def test_claim_citing_mislabeled_evidence_is_unsupported():
    """A claim can cite evidence that exists and has fine provenance, but
    whose evidence_type/directness label is itself wrong (e.g. literature
    mislabeled DIRECT) — that must also make the citing claim unsupported."""
    backing = ToolResult(provider="europe_pmc", operation="search", status=ToolStatus.OK, latency_ms=1.0, data={})
    bad_evidence = EvidenceRecord(
        evidence_id="ev1", source="europe_pmc", source_type="literature",
        claim="mislabeled", evidence_type=EvidenceType.LITERATURE,
        evidence_level=EvidenceLevel.CURATED, directness=Directness.DIRECT,  # WRONG: must be INDIRECT
    )
    state = InvestigationState(
        raw_sequence="MKV",
        tool_results=[backing],
        evidence=[bad_evidence],
        claims=[Claim(statement="x", supporting_evidence_ids=["ev1"], agreement=AgreementLevel.AGREE)],
    )
    assert check_unsupported_claims(state)[0].unsupported is True


# --- cross-source consistency classification (Metric 5) --------------------


def test_cross_source_consistency_classifications():
    def state_with(agreements):
        return InvestigationState(raw_sequence="MKV", claims=[Claim(statement="x", agreement=a) for a in agreements])

    assert classify_cross_source_consistency(state_with([])) == "insufficient_evidence"
    assert classify_cross_source_consistency(state_with([AgreementLevel.AGREE])) == "agreement"
    assert classify_cross_source_consistency(state_with([AgreementLevel.CONFLICT])) == "disagreement"
    assert classify_cross_source_consistency(state_with([AgreementLevel.AGREE, AgreementLevel.CONFLICT])) == "disagreement"
    assert classify_cross_source_consistency(state_with([AgreementLevel.PARTIAL])) == "incomparable"
    assert classify_cross_source_consistency(state_with([AgreementLevel.UNVERIFIABLE])) == "insufficient_evidence"


# --- end-to-end (Metric 10) -------------------------------------------------


def test_end_to_end_not_evaluated_when_final_behavior_unset():
    case = _case(final_behavior="not_evaluated")
    state = InvestigationState(raw_sequence="MKV", status=InvestigationStatus.SUPPORTED)
    expected, actual, match = check_end_to_end(case, state)
    assert expected is None and match is None
    assert actual == "supported"


def test_end_to_end_matches_when_status_equals_expectation():
    case = _case(final_behavior="insufficient_evidence")
    state = InvestigationState(raw_sequence="MKV", status=InvestigationStatus.INSUFFICIENT_EVIDENCE)
    expected, actual, match = check_end_to_end(case, state)
    assert expected == "insufficient_evidence"
    assert match is True


def test_end_to_end_mismatches_when_status_differs():
    case = _case(final_behavior="supported")
    state = InvestigationState(raw_sequence="MKV", status=InvestigationStatus.FAILED)
    _, _, match = check_end_to_end(case, state)
    assert match is False
