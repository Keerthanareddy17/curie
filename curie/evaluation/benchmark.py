"""The scientific/evidence benchmark: run curie/evaluation/datasets/cases.json
through the REAL graph against LIVE UniProt/IEDB/Europe PMC/ESM Atlas, then
score each run with curie/evaluation/metrics/metrics.py.

Distinct from curie/evaluation/scenarios/fault_scenarios.py (the behavioral
reliability benchmark, which uses deterministic fixtures) — this module never
imports curie/evaluation/fixtures/. See curie/evaluation/README.md's "LIVE
INTEGRATIONS vs CONTROLLED EVALUATION FIXTURES" section.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from curie.agent.graph import run_investigation
from curie.agent.state import InvestigationState
from curie.evaluation.metrics.metrics import CaseEvaluation, evaluate_case
from curie.evaluation.models import BenchmarkCase
from curie.shared.logging import get_logger

logger = get_logger(__name__)

DATASET_PATH = Path(__file__).parent / "datasets" / "cases.json"


def load_cases(path: Path = DATASET_PATH) -> list[BenchmarkCase]:
    data = json.loads(path.read_text())
    return [BenchmarkCase.model_validate(c) for c in data["cases"]]


@dataclass
class BenchmarkCaseRun:
    case: BenchmarkCase
    state: InvestigationState
    evaluation: CaseEvaluation


async def run_case(case: BenchmarkCase) -> BenchmarkCaseRun:
    logger.info("benchmark_case_start", case_id=case.case_id, sequence_length=len(case.sequence))
    state = await run_investigation(case.sequence, accession_hint=case.accession_hint)
    evaluation = evaluate_case(case, state)
    logger.info(
        "benchmark_case_done",
        case_id=case.case_id,
        run_id=state.run_id,
        status=state.status.value,
        evidence_score=state.evidence_score,
    )
    return BenchmarkCaseRun(case=case, state=state, evaluation=evaluation)


async def run_benchmark(cases: list[BenchmarkCase] | None = None) -> list[BenchmarkCaseRun]:
    cases = cases if cases is not None else load_cases()
    return [await run_case(case) for case in cases]
