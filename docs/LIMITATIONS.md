# Research-Use Limitation

curie is a research and education prototype built for a hackathon. It is **not**:

- A clinical decision-support tool.
- A source of therapeutic or vaccine-design recommendations.
- Wet-lab ready. No output from curie should be synthesized, expressed, or administered.
- A replacement for peer-reviewed bioinformatics tools (IEDB's own predictors, AlphaFold/ESMFold
  papers, UniProt curation, etc.) — curie calls out to some of these systems, but composing their
  outputs into a narrative is not the same as validating a scientific claim.

curie's stated goal is narrower and more honest than "design a vaccine": given a protein sequence,
investigate it across independent public evidence sources (structure prediction, sequence/function
annotation, epitope evidence, literature) and make explicit, and checkable, how much those sources
agree — rather than presenting a single fluent narrative as if it were settled.

Any dossier, score, or "confidence" value curie produces is a computed summary of what its tools
returned at run time, tagged with provenance (`provider`, `operation`, `status`, `latency_ms`,
`request_id`, `error`). It is not a claim of biological truth.

## Identity resolution

curie does not perform sequence-to-accession identity resolution (e.g. BLAST-style
homology search). Identity is only ever established when a caller supplies a known
`accession_hint`, confirmed against a real UniProt lookup. Without one,
`identity_status` stays `UNRESOLVED` — the correct, honest behavior, not a shortfall.
`curie/evaluation/` enforces this mechanically: a benchmark case that supplies
`accession_hint` is tagged `identity_supplied` and is never counted toward
identity-resolution accuracy, precisely to avoid rewarding the system for information
the evaluator handed it directly. See `curie/evaluation/README.md`.

## evidence_score is not a calibrated probability

`evidence_score` (and the `InvestigationStatus` it feeds via
`curie/agent/nodes/confidence_gate.py`) is a deterministic, reproducible function of
tool-call outcomes and cross-source agreement (`curie/evaluation/reliability.py`). It
is not a calibrated probability of biological correctness, and nothing in curie should
be read as claiming a score of e.g. `0.84` means "84% likely to be true."

One concrete consequence, found while building Phase 3's evaluation harness: once an
`accession_hint` resolves via UniProt, the scorer's floor sits at roughly 0.625 — above
the threshold for abstaining into `INSUFFICIENT_EVIDENCE` — regardless of how many of
the *other* three tools subsequently fail. A run with a resolved identity can currently
degrade to `PARTIALLY_SUPPORTED` at worst; it cannot abstain the way an unresolved-identity
run can. This is a real property of the current scoring design, not a bug fixed in this
phase (changing it specifically to alter evaluation outcomes is exactly what the
evaluation is meant to catch, not what should motivate a fix) — flagged here as the
top scoring-logic risk for whoever revisits `confidence_gate.py` next.

## A bug the evaluation found and fixed

Building the fault-injection scenarios in Phase 3 surfaced a real, previously invisible
bug: `curie/tools/evidence_verification.py`'s `verify_identity_consistency` assumed
UniProt's *search*-response shape (`{"results": [...]}`), but the actual calling code
(`curie/agent/nodes/identity_resolution.py`) uses `UniProtClient.get_entry`, which
returns a bare single-record dict. The check silently extracted zero names on every
real run and always returned `UNVERIFIABLE` — never actually comparing UniProt's and
IEDB's protein names — from Phase 2 onward, until Phase 3's Scenario D (deliberately
conflicting sources) caught it by producing no conflict when one was clearly expected.
Fixed, with regression tests, in the same change; see `curie/evaluation/README.md`.

## Benchmark selection

The 6 real proteins in `curie/evaluation/datasets/cases.json` were deliberately chosen
as well-characterized model antigens/viral targets with rich public UniProt/IEDB/
literature coverage. A near-100% result on them (see
`curie/evaluation/results/latest.md`) reflects correct behavior on well-documented
proteins — it is not evidence of how curie performs on obscure or sparsely-annotated
ones, which this evaluation does not yet test.
