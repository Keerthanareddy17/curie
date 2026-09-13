from curie.evaluation.reliability import score_run
from curie.shared.models import AgreementLevel, ToolResult, ToolStatus, VerificationFinding


def _result(status: ToolStatus) -> ToolResult:
    return ToolResult(provider="p", operation="op", status=status, latency_ms=5.0)


def _finding(agreement: AgreementLevel) -> VerificationFinding:
    return VerificationFinding(claim="c", agreement=agreement)


def test_score_run_all_ok_all_agree_is_high_confidence():
    report = score_run(
        [_result(ToolStatus.OK), _result(ToolStatus.OK)],
        [_finding(AgreementLevel.AGREE), _finding(AgreementLevel.AGREE)],
    )
    assert report.tool_success_rate == 1.0
    assert report.agreement_rate == 1.0
    assert report.confidence_score == 1.0
    assert report.caveats == []


def test_score_run_no_tool_calls_is_zero_confidence_with_caveat():
    report = score_run([], [])
    assert report.tool_success_rate == 0.0
    assert report.confidence_score == 0.0
    assert "No verification findings" in " ".join(report.caveats)


def test_score_run_failed_tool_lowers_confidence_and_adds_caveat():
    report = score_run(
        [_result(ToolStatus.OK), _result(ToolStatus.ERROR)],
        [_finding(AgreementLevel.AGREE)],
    )
    assert report.tools_failed == 1
    assert report.tool_success_rate == 0.5
    assert any("failed or timed out" in c for c in report.caveats)


def test_score_run_conflict_lowers_agreement_and_adds_caveat():
    report = score_run(
        [_result(ToolStatus.OK)],
        [_finding(AgreementLevel.AGREE), _finding(AgreementLevel.CONFLICT)],
    )
    assert report.agreement_rate == 0.5
    assert any("conflict" in c for c in report.caveats)


def test_score_run_not_implemented_is_reported_but_not_counted_as_failure():
    report = score_run([_result(ToolStatus.NOT_IMPLEMENTED)], [])
    assert report.tools_failed == 0
    assert report.tools_not_implemented == 1
    assert any("interface stub" in c for c in report.caveats)


def test_score_run_unverifiable_findings_are_flagged():
    report = score_run([_result(ToolStatus.OK)], [_finding(AgreementLevel.UNVERIFIABLE)])
    assert report.findings_unverifiable == 1
    assert any("could not be verified" in c for c in report.caveats)
