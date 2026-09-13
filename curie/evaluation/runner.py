"""curie's evaluation CLI.

    python -m curie.evaluation.runner            # everything (default)
    python -m curie.evaluation.runner --all       # same, explicit
    python -m curie.evaluation.runner --offline   # fault scenarios only (no network)
    python -m curie.evaluation.runner --faults    # same as --offline

A thin top-level shim (`evaluation/runner.py` at the repo root) also makes
`python -m evaluation.runner` work, delegating here — see evaluation/README.md
at the repo root for why the real implementation lives under curie/.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from curie.evaluation.benchmark import load_cases, run_case
from curie.evaluation.report import build_report, write_report
from curie.evaluation.scenarios.fault_scenarios import run_all_scenarios
from curie.shared.config import get_settings
from curie.shared.logging import configure_logging, get_logger

logger = get_logger(__name__)


async def _run(include_benchmark: bool, include_scenarios: bool) -> dict:
    case_runs = []
    if include_benchmark:
        cases = load_cases()
        print(f"Running {len(cases)} scientific/evidence benchmark case(s) against LIVE APIs...")
        for case in cases:
            print(f"  - {case.case_id} ...", end=" ", flush=True)
            run = await run_case(case)
            print(f"status={run.state.status.value} evidence_score={run.state.evidence_score}")
            case_runs.append(run)

    scenario_results = []
    if include_scenarios:
        print(f"\nRunning 8 fault-injection scenarios against CONTROLLED FIXTURES (no network)...")
        scenario_results = await run_all_scenarios()
        for r in scenario_results:
            mark = "PASS" if r.passed else ("CRASHED" if r.crashed else "FAIL")
            print(f"  - [{mark}] {r.scenario_id}: {r.title}")

    return build_report(case_runs, scenario_results)


def _print_summary(report: dict) -> None:
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, value in report["metrics"].items():
        display = "NOT EVALUATED" if value is None else f"{value * 100:.1f}%"
        print(f"  {name}: {display}")


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    configure_logging(level=settings.log_level, fmt=settings.log_format)

    parser = argparse.ArgumentParser(
        prog="curie.evaluation.runner",
        description="Run curie's reliability & evaluation harness.",
    )
    parser.add_argument("--all", action="store_true", help="run everything (default)")
    parser.add_argument(
        "--offline", action="store_true", help="fault scenarios only — no network access needed"
    )
    parser.add_argument("--faults", action="store_true", help="same as --offline")
    args = parser.parse_args(argv)

    offline_only = args.offline or args.faults
    include_benchmark = not offline_only
    include_scenarios = True  # always run; they're fast and free

    report = asyncio.run(_run(include_benchmark=include_benchmark, include_scenarios=include_scenarios))
    json_path, md_path = write_report(report)

    _print_summary(report)
    print(f"\nJSON report: {json_path}")
    print(f"Markdown report: {md_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
