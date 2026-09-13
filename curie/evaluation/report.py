"""Turn benchmark case runs + fault-scenario results into the machine-readable
JSON (evaluation/results/latest.json) and human-readable Markdown (evaluation/
results/latest.md) reports.

Every number here is computed from the CaseEvaluation/ScenarioResult objects
passed in — nothing is hardcoded, and a metric with no legitimate denominator
comes back `None` (serialized as `null` in the JSON), never a fabricated 0.0
or 1.0. See curie/evaluation/README.md for what "legitimately evaluable" means
for each metric.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from curie.evaluation.benchmark import BenchmarkCaseRun
from curie.evaluation.metrics.metrics import CaseEvaluation
from curie.evaluation.models import IdentityEvalClass, ScenarioResult

RESULTS_DIR = Path(__file__).parent / "results"


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 3) if denominator else None


# --- Metrics 1-5, 9 (scientific/evidence benchmark) -------------------------


def _source_retrieval(evaluations: list[CaseEvaluation]) -> dict:
    counts = {"PASS": 0, "FAILED": 0, "SKIPPED_CORRECTLY": 0, "NOT_EVALUATED": 0}
    for ev in evaluations:
        for sc in ev.source_checks:
            counts[sc.outcome] += 1
    return {
        "value": _ratio(counts["PASS"], counts["PASS"] + counts["FAILED"]),
        "note": "Numerator/denominator exclude SKIPPED_CORRECTLY (the planner "
        "correctly decided a source was irrelevant) and NOT_EVALUATED "
        "(no expectation set for that case) per spec section 4/Metric 1.",
        **{k.lower(): v for k, v in counts.items()},
    }


def _provenance_validity(evaluations: list[CaseEvaluation]) -> dict:
    valid = total = 0
    failing_examples = []
    for ev in evaluations:
        for p in ev.provenance_checks:
            total += 1
            valid += int(p.valid)
            if not p.valid:
                failing_examples.append({"case_id": ev.case_id, "evidence_id": p.evidence_id, "reasons": p.reasons})
    return {
        "value": _ratio(valid, total),
        "valid": valid,
        "total": total,
        "failing_examples": failing_examples,
    }


def _evidence_type_correctness(evaluations: list[CaseEvaluation]) -> dict:
    correct = total = 0
    failing_examples = []
    for ev in evaluations:
        for t in ev.evidence_type_checks:
            total += 1
            correct += int(t.correct)
            if not t.correct:
                failing_examples.append({"case_id": ev.case_id, "evidence_id": t.evidence_id, "reason": t.reason})
    return {"value": _ratio(correct, total), "correct": correct, "total": total, "failing_examples": failing_examples}


def _evidence_grounding(evaluations: list[CaseEvaluation]) -> dict:
    grounded = total = 0
    failing_examples = []
    for ev in evaluations:
        for g in ev.claim_grounding_checks:
            total += 1
            grounded += int(g.grounded)
            if not g.grounded:
                failing_examples.append({"case_id": ev.case_id, "claim_id": g.claim_id, "reason": g.reason})
    return {"value": _ratio(grounded, total), "grounded": grounded, "total": total, "failing_examples": failing_examples}


def _unsupported_claim_rate(evaluations: list[CaseEvaluation], scenario_results: list[ScenarioResult]) -> dict:
    unsupported = total = 0
    failing_examples = []
    for ev in evaluations:
        for u in ev.unsupported_claim_checks:
            total += 1
            unsupported += int(u.unsupported)
            if u.unsupported:
                failing_examples.append({"case_id": ev.case_id, "claim_id": u.claim_id, "reason": u.reason})
    return {
        "value": _ratio(unsupported, total),
        "unsupported": unsupported,
        "total": total,
        "failing_examples": failing_examples,
        "note": "Computed over the scientific/evidence benchmark's claims only "
        "(fault scenarios reuse the same claim-generation code path, already "
        "covered by curie/evaluation/scenarios/fault_scenarios.py's own checks).",
    }


def _cross_source_consistency(evaluations: list[CaseEvaluation]) -> dict:
    counts = {"agreement": 0, "disagreement": 0, "incomparable": 0, "insufficient_evidence": 0}
    for ev in evaluations:
        counts[ev.cross_source_consistency] += 1
    scorable = counts["agreement"] + counts["disagreement"]
    return {"value": _ratio(counts["agreement"], scorable), **counts}


# --- Metrics 6-8, 10 (span both benchmark and fault scenarios) --------------


def _conflict_detection(scenario_results: list[ScenarioResult]) -> dict:
    positives = [s for s in scenario_results if "conflict_expected" in s.tags]
    negatives = [s for s in scenario_results if "conflict_not_expected" in s.tags]
    if not positives:
        return {"value": None, "note": "No scenario carries a known conflict label; not_evaluated."}

    true_positive = sum(1 for s in positives if s.conflict_detected)
    false_negative = sum(1 for s in positives if not s.conflict_detected)
    false_positive = sum(1 for s in negatives if s.conflict_detected)
    true_negative = sum(1 for s in negatives if not s.conflict_detected)

    precision = _ratio(true_positive, true_positive + false_positive)
    recall = _ratio(true_positive, true_positive + false_negative)
    return {
        "value": recall,  # single headline number = recall on the known-positive scenario(s)
        "precision": precision,
        "recall": recall,
        "true_positive": true_positive,
        "false_negative": false_negative,
        "false_positive": false_positive,
        "true_negative": true_negative,
        "note": "Computed only over curie/evaluation/scenarios/fault_scenarios.py, "
        "the only place with a known ground-truth conflict label (Scenario D). "
        "The scientific benchmark's real-world cases have no such label and do "
        "not contribute here, per spec section 5/Metric 6.",
    }


def _abstention_correctness(evaluations: list[CaseEvaluation], scenario_results: list[ScenarioResult]) -> dict:
    benchmark_abstention = [ev for ev in evaluations if ev.end_to_end_expected == "insufficient_evidence"]
    scenario_abstention = [s for s in scenario_results if "abstention_expected" in s.tags]

    total = len(benchmark_abstention) + len(scenario_abstention)
    if total == 0:
        return {"value": None, "note": "No case/scenario has a defined abstention expectation."}

    correct = sum(1 for ev in benchmark_abstention if ev.end_to_end_match) + sum(
        1 for s in scenario_abstention if s.final_status == "insufficient_evidence"
    )
    return {
        "value": _ratio(correct, total),
        "correct": correct,
        "total": total,
        "from_benchmark_cases": len(benchmark_abstention),
        "from_fault_scenarios": len(scenario_abstention),
    }


def _tool_recovery_success(scenario_results: list[ScenarioResult]) -> dict:
    recovery_scenarios = [s for s in scenario_results if "tool_recovery" in s.tags]
    if not recovery_scenarios:
        return {"value": None, "note": "No scenario is tagged tool_recovery."}
    passed = sum(1 for s in recovery_scenarios if s.passed)
    return {
        "value": _ratio(passed, len(recovery_scenarios)),
        "passed": passed,
        "total": len(recovery_scenarios),
        "scenario_ids": [s.scenario_id for s in recovery_scenarios],
    }


def _end_to_end_success(evaluations: list[CaseEvaluation], scenario_results: list[ScenarioResult]) -> dict:
    benchmark_matches = [ev.end_to_end_match for ev in evaluations if ev.end_to_end_match is not None]
    scenario_matches = [s.passed for s in scenario_results]
    all_matches = benchmark_matches + scenario_matches
    correct = sum(1 for m in all_matches if m)
    return {
        "value": _ratio(correct, len(all_matches)),
        "correct": correct,
        "total": len(all_matches),
        "from_benchmark_cases": len(benchmark_matches),
        "from_fault_scenarios": len(scenario_matches),
        "note": "Benchmark cases only contribute where final_behavior is not "
        "'not_evaluated' (see curie/evaluation/datasets/README.md for why "
        "most happy-path cases leave it unset).",
    }


def _identity_evaluation_breakdown(evaluations: list[CaseEvaluation]) -> dict:
    counts = {c.value: 0 for c in IdentityEvalClass}
    for ev in evaluations:
        counts[ev.identity_eval_class.value] += 1
    return {
        **counts,
        "note": "identity_supplied cases are NEVER counted toward identity-"
        "resolution accuracy — see spec section 6 / docs/LIMITATIONS.md. "
        "curie does not currently implement sequence-to-accession resolution, "
        "so identity_resolved (independent success) is not reachable today; "
        "this is documented, not hidden.",
    }


def build_report(
    case_runs: list[BenchmarkCaseRun], scenario_results: list[ScenarioResult]
) -> dict:
    evaluations = [run.evaluation for run in case_runs]

    metrics = {
        "source_retrieval_success": _source_retrieval(evaluations),
        "provenance_validity": _provenance_validity(evaluations),
        "evidence_grounding_rate": _evidence_grounding(evaluations),
        "evidence_type_correctness": _evidence_type_correctness(evaluations),
        "cross_source_consistency": _cross_source_consistency(evaluations),
        "conflict_detection": _conflict_detection(scenario_results),
        "abstention_correctness": _abstention_correctness(evaluations, scenario_results),
        "tool_recovery_success": _tool_recovery_success(scenario_results),
        "unsupported_claim_rate": _unsupported_claim_rate(evaluations, scenario_results),
        "end_to_end_success": _end_to_end_success(evaluations, scenario_results),
    }

    return {
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "cases_evaluated": len(case_runs),
        "scenarios_evaluated": len(scenario_results),
        "metrics": {k: v["value"] for k, v in metrics.items()},
        "metrics_detail": metrics,
        "identity_evaluation_breakdown": _identity_evaluation_breakdown(evaluations),
        "cases": [
            {
                "case_id": run.case.case_id,
                "run_id": run.state.run_id,
                "sequence_length": len(run.case.sequence),
                "accession_hint": run.case.accession_hint,
                "identity_eval_class": run.evaluation.identity_eval_class.value,
                "final_status": run.state.status.value,
                "evidence_score": run.state.evidence_score,
                "evidence_count": len(run.state.evidence),
                "conflicts": len(run.state.conflicts),
                "tool_statuses": {r.provider: r.status.value for r in run.state.tool_results},
                "end_to_end_expected": run.evaluation.end_to_end_expected,
                "end_to_end_match": run.evaluation.end_to_end_match,
                "source_checks": [
                    {"source": c.source, "outcome": c.outcome, "detail": c.detail} for c in run.evaluation.source_checks
                ],
            }
            for run in case_runs
        ],
        "reliability_scenarios": [
            {
                "scenario_id": s.scenario_id,
                "title": s.title,
                "injected_fault": s.injected_fault,
                "expected_behavior": s.expected_behavior,
                "actual_behavior": s.actual_behavior,
                "passed": s.passed,
                "crashed": s.crashed,
                "run_id": s.run_id,
                "checks": [{"description": c.description, "passed": c.passed, "detail": c.detail} for c in s.checks],
            }
            for s in scenario_results
        ],
        "limitations": [
            "curie does not perform sequence-to-accession identity resolution; "
            "cases/scenarios supplying accession_hint are excluded from "
            "identity-resolution accuracy scoring (identity_supplied is not "
            "identity_resolved). See docs/LIMITATIONS.md.",
            "evidence_score / confidence_class are internal, deterministic "
            "evidence-support scores, not calibrated probabilities of "
            "biological truth. See curie/agent/nodes/confidence_gate.py.",
            "end_to_end_success only scores cases/scenarios with a defined "
            "expected final status; 5 of 6 scientific-benchmark cases leave "
            "it 'not_evaluated' because their exact outcome depends on live "
            "API text this evaluation does not control in advance (see "
            "curie/evaluation/datasets/README.md).",
            "A previously undetected bug (verify_identity_consistency assumed "
            "a UniProt *search* response shape but the real code path uses "
            "get_entry, a differently-shaped single record) meant the "
            "identity-consistency cross-check always returned UNVERIFIABLE on "
            "every real run prior to this evaluation phase. Found via fault-"
            "injection testing and fixed in curie/tools/evidence_verification.py; "
            "see docs/LIMITATIONS.md and the Phase 3 report for detail.",
            "The 6 scientific-benchmark proteins were deliberately chosen "
            "because they are well-characterized model antigens/viral targets "
            "with rich public UniProt/IEDB/literature coverage (see curie/"
            "evaluation/datasets/README.md) — a near-100% result here "
            "reflects correct behavior on well-documented proteins, not a "
            "claim that curie performs this well on obscure or sparsely-"
            "annotated ones, which this evaluation does not test.",
            "Once an accession_hint resolves via UniProt, curie/evaluation/"
            "reliability.py's score_run gives a confidence floor of ~0.625 "
            "(0.5 x agreement_rate=1.0 from the always-AGREE identity_resolved "
            "finding, plus >=0 tool_success_rate) — meaning a run with a "
            "resolved identity can currently degrade to PARTIALLY_SUPPORTED at "
            "worst, never abstain into INSUFFICIENT_EVIDENCE, no matter how "
            "many of the other three tools fail. Confirmed analytically and "
            "not exercised by any scenario here (Scenario E and the no-hint "
            "benchmark case both test the unresolved-identity path instead). "
            "This is the top scoring-logic risk carried into Phase 4.",
        ],
    }


def write_report(report: dict, results_dir: Path = RESULTS_DIR) -> tuple[Path, Path]:
    results_dir.mkdir(parents=True, exist_ok=True)
    json_path = results_dir / "latest.json"
    md_path = results_dir / "latest.md"
    json_path.write_text(json.dumps(report, indent=2, default=str) + "\n")
    md_path.write_text(render_markdown(report))
    return json_path, md_path


def _fmt_pct(value: float | None) -> str:
    return "NOT EVALUATED" if value is None else f"{value * 100:.1f}%"


def render_markdown(report: dict) -> str:
    m = report["metrics"]
    lines: list[str] = []
    lines.append("# curie evaluation report")
    lines.append("")
    lines.append(f"Generated: {report['run_timestamp']}")
    lines.append("")

    lines.append("## Executive summary")
    lines.append("")
    lines.append(f"- Scientific/evidence benchmark cases evaluated: **{report['cases_evaluated']}**")
    lines.append(f"- Behavioral reliability scenarios evaluated: **{report['scenarios_evaluated']}**")
    lines.append(f"- End-to-end success: **{_fmt_pct(m['end_to_end_success'])}**")
    lines.append(f"- Evidence grounding rate: **{_fmt_pct(m['evidence_grounding_rate'])}**")
    lines.append(f"- Provenance validity: **{_fmt_pct(m['provenance_validity'])}**")
    lines.append(f"- Abstention correctness: **{_fmt_pct(m['abstention_correctness'])}**")
    lines.append(f"- Tool recovery success: **{_fmt_pct(m['tool_recovery_success'])}**")
    lines.append(f"- Unsupported claim rate: **{_fmt_pct(m['unsupported_claim_rate'])}** (lower is better)")
    lines.append("")

    lines.append("## Benchmark methodology")
    lines.append("")
    lines.append(
        "Two complementary evaluation classes, per project spec section 3:\n\n"
        "1. **Scientific/evidence benchmark** (`curie/evaluation/datasets/cases.json`, "
        "6 real proteins, run against LIVE UniProt/IEDB/Europe PMC/ESM Atlas): "
        "source retrieval, provenance, evidence grounding, evidence-type "
        "correctness, cross-source consistency, unsupported-claim rate.\n"
        "2. **Behavioral reliability benchmark** (`curie/evaluation/scenarios/"
        "fault_scenarios.py`, 8 deterministic fault-injection scenarios, tool "
        "clients mocked): conflict detection, abstention correctness, tool "
        "recovery.\n\n"
        "See `curie/evaluation/datasets/README.md` and `curie/evaluation/"
        "fixtures/README.md` for exactly how ground truth was sourced and why "
        "some fields are intentionally `not_evaluated` rather than guessed."
    )
    lines.append("")

    lines.append("## Identity evaluation (no free information)")
    lines.append("")
    idb = report["identity_evaluation_breakdown"]
    lines.append(f"- `identity_supplied`: {idb['identity_supplied']} (excluded from any accuracy scoring)")
    lines.append(f"- `identity_resolved`: {idb['identity_resolved']} (independent resolution — not implemented today)")
    lines.append(f"- `identity_unresolved`: {idb['identity_unresolved']} (correct behavior without a hint)")
    lines.append(f"- `identity_not_evaluated`: {idb['identity_not_evaluated']}")
    lines.append("")
    lines.append(f"> {idb['note']}")
    lines.append("")

    lines.append("## Scientific/evidence results")
    lines.append("")
    lines.append("| Case | Accession hint | Final status | Evidence score | Conflicts | End-to-end match |")
    lines.append("|---|---|---|---|---|---|")
    for c in report["cases"]:
        match = "n/a" if c["end_to_end_match"] is None else ("✅" if c["end_to_end_match"] else "❌")
        lines.append(
            f"| {c['case_id']} | {c['accession_hint'] or '—'} | {c['final_status']} | "
            f"{c['evidence_score']} | {c['conflicts']} | {match} |"
        )
    lines.append("")

    lines.append("## Reliability results (fault injection)")
    lines.append("")
    lines.append("| Scenario | Injected fault | Expected | Actual | Pass |")
    lines.append("|---|---|---|---|---|")
    for s in report["reliability_scenarios"]:
        mark = "✅" if s["passed"] else ("💥 CRASHED" if s["crashed"] else "❌")
        lines.append(f"| {s['scenario_id']}: {s['title']} | {s['injected_fault']} | {s['expected_behavior']} | {s['actual_behavior']} | {mark} |")
    lines.append("")

    failed = [s for s in report["reliability_scenarios"] if not s["passed"]] + [
        c for c in report["cases"] if c["end_to_end_match"] is False
    ]
    lines.append("## Failure analysis")
    lines.append("")
    if not failed:
        lines.append("No scenario or benchmark case with a defined expectation failed on this run.")
    else:
        for item in failed:
            lines.append(f"- **{item.get('scenario_id') or item.get('case_id')}**: see checks/detail above for what failed and why.")
    lines.append("")

    lines.append("## Limitations")
    lines.append("")
    for limitation in report["limitations"]:
        lines.append(f"- {limitation}")
    lines.append("")

    return "\n".join(lines)
