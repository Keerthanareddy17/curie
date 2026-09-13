import json

from curie.agent.state import InvestigationState
from curie.evaluation.benchmark import BenchmarkCaseRun
from curie.evaluation.metrics.metrics import evaluate_case
from curie.evaluation.models import (
    BenchmarkCase,
    EvidenceExpectation,
    ExpectedOutcome,
    ScenarioCheck,
    ScenarioResult,
)
from curie.evaluation.report import build_report, render_markdown, write_report
from curie.shared.models import InvestigationStatus, ToolResult, ToolStatus


def _fake_case_run() -> BenchmarkCaseRun:
    case = BenchmarkCase(
        case_id="fake_case",
        description="fake",
        sequence="MKV",
        expected=ExpectedOutcome(
            evidence_expectations=[EvidenceExpectation(source="uniprot", expect_status="ok")],
            final_behavior="not_evaluated",
        ),
    )
    state = InvestigationState(
        raw_sequence="MKV",
        normalized_sequence="MKV",
        status=InvestigationStatus.SUPPORTED,
        evidence_score=0.9,
        tool_results=[ToolResult(provider="uniprot", operation="get_entry", status=ToolStatus.OK, latency_ms=1.0)],
    )
    return BenchmarkCaseRun(case=case, state=state, evaluation=evaluate_case(case, state))


def _fake_scenario_result(passed: bool) -> ScenarioResult:
    return ScenarioResult(
        scenario_id="Z",
        title="fake scenario",
        injected_fault="none",
        expected_behavior="passes",
        actual_behavior="passed" if passed else "failed",
        passed=passed,
        checks=[ScenarioCheck(description="dummy", passed=passed)],
    )


def test_build_report_has_all_required_metric_keys():
    report = build_report([_fake_case_run()], [_fake_scenario_result(True)])
    expected_keys = {
        "source_retrieval_success", "provenance_validity", "evidence_grounding_rate",
        "evidence_type_correctness", "cross_source_consistency", "conflict_detection",
        "abstention_correctness", "tool_recovery_success", "unsupported_claim_rate",
        "end_to_end_success",
    }
    assert expected_keys == set(report["metrics"].keys())


def test_build_report_metric_with_no_denominator_is_null_not_fabricated():
    # No scenario tagged conflict_expected -> conflict_detection must be null, never 0.0 or 1.0.
    report = build_report([_fake_case_run()], [_fake_scenario_result(True)])
    assert report["metrics"]["conflict_detection"] is None
    assert report["metrics"]["tool_recovery_success"] is None  # no scenario tagged tool_recovery either


def test_build_report_is_json_serializable(tmp_path):
    report = build_report([_fake_case_run()], [_fake_scenario_result(True)])
    json_path, md_path = write_report(report, results_dir=tmp_path)

    assert json_path.exists() and md_path.exists()
    reloaded = json.loads(json_path.read_text())
    assert reloaded["cases_evaluated"] == 1
    assert reloaded["metrics"]["conflict_detection"] is None  # null survives JSON round-trip


def test_render_markdown_contains_expected_sections():
    report = build_report([_fake_case_run()], [_fake_scenario_result(True)])
    md = render_markdown(report)
    for heading in (
        "Executive summary", "Benchmark methodology", "Identity evaluation",
        "Scientific/evidence results", "Reliability results", "Failure analysis", "Limitations",
    ):
        assert heading in md


def test_render_markdown_shows_not_evaluated_for_null_metrics():
    report = build_report([_fake_case_run()], [_fake_scenario_result(True)])
    md = render_markdown(report)
    assert "NOT EVALUATED" in md
