# Reliability: how do we know curie works?

We don't trust the model's confidence. We measure the system's behavior.

1. **We test the final outcome** — 6 real proteins (SARS-CoV-2 Spike RBD, ovalbumin,
   lysozyme, insulin, HIV gp160) run against LIVE UniProt/IEDB/Europe PMC/ESM Atlas.
2. **We test the agent's behavior** — 8 deterministic fault-injection scenarios assert
   which tools should run, skip, or fail, not just what the final text says.
3. **We test its evidence grounding** — every claim the adjudicator emits must cite an
   `evidence_id` that traces to a real, successful `ToolResult`; a claim citing nothing,
   or citing evidence that fails provenance, is caught mechanically (`check_claim_grounding`,
   `curie/evaluation/metrics/metrics.py`).
4. **We test its failure behavior** — timeouts, malformed 200-OK payloads, oversized
   sequences, and dead services are injected via `curie/evaluation/fixtures/fault_adapters.py`
   against the real, unmodified graph. No mocking of `run_investigation` itself.
5. **We test its ability to abstain** — cases/scenarios with no identity hint or
   insufficient evidence must reach `INSUFFICIENT_EVIDENCE`, not a confident guess.
6. **We test that Gemini cannot override deterministic truth** — `gemini_synthesis`
   runs strictly after `confidence_gate`; its only state field is `ai_synthesis: str | None`.
   It cannot write `evidence_score`, `status`, `conflicts`, or `provenance` — this is a type-level
   guarantee in `curie/agent/state.py`, not a prompt instruction.
7. **We rerun the same scenarios as regression tests** — `python -m curie.evaluation.runner`
   is deterministic-scenario-safe to rerun any time; results are written to
   `curie/evaluation/results/latest.json`/`.md`, never hand-edited.

## Actual results (this run)

Generated: `2026-09-13T21:47:30Z` via `python -m curie.evaluation.runner --all`
(6 live scientific-benchmark cases + 8 fault-injection scenarios)

| Metric | Result |
|---|---|
| Source retrieval success | 100.0% |
| Provenance validity | 100.0% |
| Evidence grounding rate | 100.0% |
| Evidence-type correctness | 100.0% |
| Cross-source consistency | 100.0% |
| Conflict detection | 100.0% |
| Abstention correctness | 100.0% |
| Tool recovery success | 100.0% |
| Unsupported claim rate | 0.0% (lower is better) |
| End-to-end success | 100.0% |

Full detail, per-case breakdowns, and failing-example lists (empty on this run) are in
`curie/evaluation/results/latest.json` and `latest.md` — regenerate any time with
`python -m curie.evaluation.runner --all`. See `curie/evaluation/README.md` for how
ground truth was sourced and exactly which metrics report `null` ("not evaluated")
rather than a guessed number, and `docs/LIMITATIONS.md` for what this evaluation does
not claim (e.g. curie does not do sequence-to-accession identity resolution, so
`accession_hint`-supplied cases are excluded from identity-accuracy scoring).
