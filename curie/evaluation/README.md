# curie evaluation

> Unit tests verify components. This evaluation harness measures end-to-end
> behavioral reliability — the distinction the whole hackathon judging
> criterion (reliability & evaluation) is actually asking about.

## Run it

```bash
python -m curie.evaluation.runner            # everything (default): live benchmark + fault scenarios
python -m curie.evaluation.runner --all       # same, explicit
python -m curie.evaluation.runner --offline   # fault scenarios only — no network access needed
python -m curie.evaluation.runner --faults    # same as --offline

# also works from the repo root, per the original spec's literal command:
python -m evaluation.runner
python -m evaluation.runner --offline
```

Every run writes `curie/evaluation/results/latest.json` (machine-readable) and
`curie/evaluation/results/latest.md` (human-readable) and prints a summary
telling you where they landed. Nothing is hardcoded: a metric with no
legitimate denominator comes back `null`/`NOT EVALUATED`, never a fabricated
number.

## What's being evaluated, and how

Two complementary evaluation classes (kept structurally separate, per spec):

1. **Scientific/evidence benchmark** — `curie/evaluation/benchmark.py` runs
   `curie/evaluation/datasets/cases.json` (6 real, publicly-verifiable
   proteins) through the real graph against **live** UniProt/IEDB/Europe
   PMC/ESM Atlas, then scores each run with `curie/evaluation/metrics/
   metrics.py`: source retrieval, provenance validity, evidence grounding,
   evidence-type correctness (curated vs. predicted vs. indirect), and
   cross-source consistency.
2. **Behavioral reliability benchmark** — `curie/evaluation/scenarios/
   fault_scenarios.py` runs 8 deterministic fault-injection scenarios
   (timeout, oversized input, no-match, conflicting sources, insufficient
   evidence, malformed response, homolog literature, unavailable service)
   with all four tool clients monkeypatched to **controlled fixtures**
   (`curie/evaluation/fixtures/`) — never live APIs. This is where conflict
   detection, abstention correctness, and tool-recovery are measured.

See `curie/evaluation/datasets/README.md` for exactly how each case's
expected values were sourced (always a live API check, dated, never copied
from a prior run of curie itself), and `curie/evaluation/fixtures/README.md`
for why fault injection uses fixtures rather than hoping a real API breaks.

## LIVE INTEGRATIONS vs. CONTROLLED EVALUATION FIXTURES

**Never confuse these two.** The demo/production path
(`curie/agent/`, `curie/tools/`, `python -m curie serve`) always calls the
real APIs:

- UniProt (`rest.uniprot.org`)
- IEDB (`query-api.iedb.org`)
- Europe PMC (`ebi.ac.uk/europepmc`)
- ESM Atlas (`api.esmatlas.com`)

The fault-injection scenarios monkeypatch those same four client *classes*
for the duration of one scenario only (`curie/evaluation/fixtures/
fault_adapters.py`'s `ToolPatch`), and are used **only** by
`curie/evaluation/` and its own tests — `curie/agent/` and `curie/tools/`
never import anything under `curie/evaluation/fixtures/`.

## The "no free information" rule

`accession_hint` is an input a caller supplies, not something curie
discovers. A benchmark case that supplies it is tagged `identity_supplied`
and is **never** counted toward identity-resolution accuracy — see
`curie/evaluation/models.py`'s `IdentityEvalClass` and `metrics.py`'s
`classify_identity`, and the dedicated no-hint case
(`sars_cov2_spike_rbd_no_hint`) in the dataset. curie does not currently
perform sequence-to-accession identity resolution; the report says so
explicitly rather than pretending otherwise.

## Deterministic confidence, not calibrated probability

`evidence_score` (and the `InvestigationStatus` class it feeds into via
`curie/agent/nodes/confidence_gate.py`) is an internal, reproducible
evidence-support score — computed from tool-call outcomes and cross-source
agreement (`curie/evaluation/reliability.py`'s `score_run`, unchanged since
Phase 2). **It is not a calibrated probability of biological truth.** This
evaluation tests whether the deterministic adjudicator reaches the expected
*class* of behavior for a given input, never whether `0.84` means "84%
likely to be correct" — it doesn't mean that, and nothing in this codebase
claims it does.

There is no LLM anywhere in the evaluated pipeline: `curie/agent/nodes/
dossier_generation.py` is fully templated from structured state (see its
module docstring). So there is nothing to test for "can a free-form
explanation override the evidence score" — the question doesn't apply yet.
If an LLM summarization pass is added later, it must only ever summarize;
evidence records, source identifiers, conflicts, evidence_score, and the
final status must remain untouched by it, and a test proving that should be
added at that point.

## Metrics reference

| # | Metric | Computed from | `null` when |
|---|---|---|---|
| 1 | `source_retrieval_success` | benchmark, per-source PASS/FAILED (SKIPPED_CORRECTLY and NOT_EVALUATED excluded from the ratio) | no case has an "ok"/"skipped" expectation |
| 2 | `provenance_validity` | benchmark, every non-absence EvidenceRecord | no non-absence evidence exists |
| 3 | `evidence_grounding_rate` | benchmark, every adjudicator Claim | no claims exist |
| 4 | `evidence_type_correctness` | benchmark, curated/predicted/indirect labels | no non-absence evidence exists |
| 5 | `cross_source_consistency` | benchmark, per-case AGREE/CONFLICT/PARTIAL/UNVERIFIABLE classification | no AGREE or CONFLICT claim exists anywhere |
| 6 | `conflict_detection` | fault scenarios only (Scenario D = known positive, all others = known negative) | no scenario carries a conflict label |
| 7 | `abstention_correctness` | benchmark's no-hint case + fault Scenarios C/E | no case/scenario expects abstention |
| 8 | `tool_recovery_success` | fault scenarios tagged `tool_recovery` (A, C, F, H) | none tagged |
| 9 | `unsupported_claim_rate` | benchmark, every adjudicator Claim (lower is better) | no claims exist |
| 10 | `end_to_end_success` | benchmark cases with a defined `final_behavior` + all 8 fault scenarios | no case/scenario has a defined expectation |

## Regression tests

Every fault scenario and every metric has a corresponding pytest file:
`tests/test_evaluation_scenarios.py`, `tests/test_evaluation_metrics.py`,
`tests/test_evaluation_report.py`. Run:

```bash
pytest                    # everything, including 2 live-network Phase 1/2 smoke tests
pytest -m "not network"   # fully offline — this includes ALL evaluation tests
```

The provenance and unsupported-claim checks specifically include **negative**
test cases (deliberately malformed/fabricated evidence and claims) proving
the detectors actually catch bad input — a check that always says "valid"
would also show 100% on the live benchmark's clean data, so that alone isn't
proof; see `tests/test_evaluation_metrics.py`.
