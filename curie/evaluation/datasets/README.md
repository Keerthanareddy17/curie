# Benchmark dataset

`cases.json` holds 6 real, publicly-verifiable protein cases. Quality over
quantity, per the Phase 3 spec: these are 5 distinct real proteins (one used
twice, with and without an accession hint, specifically to test the "no free
information" rule below), not 50 shallow ones.

## Where every field came from

Every sequence is the exact, unmodified UniProt sequence for its accession
(fetched via `https://rest.uniprot.org/uniprotkb/{accession}.fasta`), or the
literature-standard receptor-binding-domain slice of one (SARS-CoV-2 Spike
RBD, residues 319-541 — the boundary used in the structural literature, e.g.
Lan et al. 2020, *Nature*). No sequence was invented or paraphrased.

Every `evidence_expectations` entry was verified against the **live** API
immediately before being written into this file (dated 2026-09-13 in each
entry's `notes`) — e.g. confirming IEDB actually returns a non-empty curated
epitope set for a given accession, or that Europe PMC actually returns a
non-trivial hit count for a given protein name + "epitope" query. These are
not assumptions; each one is a one-line `curl` check recorded in the case's
notes field, reproducible by anyone.

## The "no free information" rule (Phase 3 spec section 6)

`sars_cov2_spike_rbd_no_hint` uses the identical sequence to
`sars_cov2_spike_rbd_with_hint` but omits `accession_hint`. Its `expected.
identity.accession` field (P0DTC2) exists **only so the report can note what
the true identity is**, for a reader's context — it is never given to curie
as input, and it is never scored as an identity-resolution success. curie
does not perform sequence-homology search (see `docs/LIMITATIONS.md`), so
`expected.identity.status` is `"unresolved"`, and that is the *correct*,
passing outcome — not a shortfall. See `curie/evaluation/metrics/metrics.py`
(`classify_identity`) for how this is enforced mechanically, not just
documented.

## `final_behavior`: why it is `"not_evaluated"` for 5 of 6 cases

`final_behavior` (the expected final `InvestigationStatus`) is filled in only
where it is analytically guaranteed by curie's documented, deterministic
confidence-gate rules (`curie/agent/nodes/confidence_gate.py`) applied to a
case's *known, fixed input conditions* — never by running curie once and
copying whatever it produced.

For `sars_cov2_spike_rbd_no_hint`, this is genuinely derivable without running
anything: no accession hint means UniProt is never called, IEDB and Europe
PMC are structurally forced to `SKIPPED`, and evidence_adjudication can only
produce non-scorable (`UNVERIFIABLE`/`PARTIAL`) findings — so
`tool_success_rate` and `agreement_rate` are pinned low regardless of which
protein is used, and `confidence_gate` is guaranteed to land on
`INSUFFICIENT_EVIDENCE`. That's a property of the code, checkable by reading
it, not a guess.

For the other 5 (accession-hint-supplied, happy-path) cases, the exact final
status additionally depends on live text returned by UniProt/IEDB at run
time (the identity-consistency name-overlap check) in a way that is correct
to leave undetermined ahead of time rather than assert and risk being wrong
about text we don't control. So `final_behavior` is `"not_evaluated"` for
those 5 — end-to-end-success is only scored where a gold answer is honestly
knowable in advance. This does **not** exempt those cases from the other
metrics: source retrieval, evidence-type correctness, and provenance are all
scored for every case, because those *were* verified live in advance (see
above).

## What is deliberately NOT in this dataset

- No fault injection. Timeouts, malformed responses, and unavailable
  services are tested by `curie/evaluation/scenarios/fault_scenarios.py`
  against deterministic fixtures, never by hoping a real API breaks.
- No invented epitope sequences, no invented citations, no invented
  accessions.
