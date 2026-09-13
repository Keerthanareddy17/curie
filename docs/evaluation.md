# Evaluation

Full detail lives in [`curie/evaluation/README.md`](../curie/evaluation/README.md)
(dataset sourcing, fixtures, metrics reference, exact commands). This page is
the short version for anyone browsing `docs/`.

> Unit tests verify components. The evaluation harness measures end-to-end
> behavioral reliability.

## Run it

```bash
python -m curie.evaluation.runner        # or: python -m evaluation.runner
```

Writes `curie/evaluation/results/latest.json` and `latest.md`.

## What it covers

- **Scientific/evidence benchmark**: 6 real, publicly-verified proteins run
  against live UniProt/IEDB/Europe PMC/ESM Atlas — source retrieval,
  provenance, evidence grounding, evidence-type correctness (curated vs.
  predicted vs. indirect), cross-source consistency.
- **Behavioral reliability benchmark**: 8 deterministic fault-injection
  scenarios (timeout, oversized input, no-match, conflicting sources,
  insufficient evidence, malformed response, homolog literature, unavailable
  service) against controlled fixtures — conflict detection, abstention
  correctness, tool recovery.

## Non-negotiables this evaluation enforces

- **No free information**: a case supplying `accession_hint` is never scored
  as independently-resolved identity. curie does not implement
  sequence-to-accession resolution; the report says so rather than
  pretending.
- **No calibrated-probability claims**: `evidence_score` is a deterministic,
  reproducible evidence-support score, not "% likely to be true." See
  `curie/agent/nodes/confidence_gate.py`.
- **No mocks in the demo path**: fault-injection fixtures are used only by
  `curie/evaluation/`; the live demo always calls real APIs.
- **No hardcoded numbers**: every metric is computed from structured state;
  a metric with no legitimate denominator reports `null`, never a guess.

## A limitation this evaluation found, not hid

Building the fault-injection scenarios surfaced a real bug: `curie/tools/
evidence_verification.py`'s identity-consistency check assumed UniProt's
*search*-response shape, but the real code path (`agent/nodes/
identity_resolution.py`) calls `get_entry`, which returns a differently-shaped
single record. The check silently returned `UNVERIFIABLE` on every real run
since Phase 2, never actually comparing names. Fixed, with regression tests,
in the same change that added this evaluation harness — see
`docs/LIMITATIONS.md` and `curie/evaluation/README.md` for detail.
