# curie evaluation report

Generated: 2026-09-13T21:47:30.725605+00:00

## Executive summary

- Scientific/evidence benchmark cases evaluated: **6**
- Behavioral reliability scenarios evaluated: **8**
- End-to-end success: **100.0%**
- Evidence grounding rate: **100.0%**
- Provenance validity: **100.0%**
- Abstention correctness: **100.0%**
- Tool recovery success: **100.0%**
- Unsupported claim rate: **0.0%** (lower is better)

## Benchmark methodology

Two complementary evaluation classes, per project spec section 3:

1. **Scientific/evidence benchmark** (`curie/evaluation/datasets/cases.json`, 6 real proteins, run against LIVE UniProt/IEDB/Europe PMC/ESM Atlas): source retrieval, provenance, evidence grounding, evidence-type correctness, cross-source consistency, unsupported-claim rate.
2. **Behavioral reliability benchmark** (`curie/evaluation/scenarios/fault_scenarios.py`, 8 deterministic fault-injection scenarios, tool clients mocked): conflict detection, abstention correctness, tool recovery.

See `curie/evaluation/datasets/README.md` and `curie/evaluation/fixtures/README.md` for exactly how ground truth was sourced and why some fields are intentionally `not_evaluated` rather than guessed.

## Identity evaluation (no free information)

- `identity_supplied`: 5 (excluded from any accuracy scoring)
- `identity_resolved`: 0 (independent resolution — not implemented today)
- `identity_unresolved`: 1 (correct behavior without a hint)
- `identity_not_evaluated`: 0

> identity_supplied cases are NEVER counted toward identity-resolution accuracy — see spec section 6 / docs/LIMITATIONS.md. curie does not currently implement sequence-to-accession resolution, so identity_resolved (independent success) is not reachable today; this is documented, not hidden.

## Scientific/evidence results

| Case | Accession hint | Final status | Evidence score | Conflicts | End-to-end match |
|---|---|---|---|---|---|
| sars_cov2_spike_rbd_with_hint | P0DTC2 | supported | 1.0 | 0 | n/a |
| sars_cov2_spike_rbd_no_hint | — | insufficient_evidence | 0.25 | 0 | ✅ |
| ovalbumin_with_hint | P01012 | supported | 1.0 | 0 | n/a |
| lysozyme_with_hint | P00698 | supported | 1.0 | 0 | n/a |
| insulin_with_hint | P01308 | supported | 1.0 | 0 | n/a |
| hiv_gp160_oversized_with_hint | P04578 | supported | 0.9 | 0 | n/a |

## Reliability results (fault injection)

| Scenario | Injected fault | Expected | Actual | Pass |
|---|---|---|---|---|
| A: ESM Atlas timeout | esm_atlas.fold_sequence times out | Timeout recorded as ToolStatus.TIMEOUT; no fake structure generated; trace contains the failure; independent evidence collection continues; dossier states structural evidence is unavailable. | status=supported, evidence_score=0.875, conflicts=0, identity_status=resolved_hint | ✅ |
| B: Sequence exceeds ESM Atlas's fold-length limit | none (real code path) — a 450 aa sequence, over the 400 aa limit | ESM Atlas is SKIPPED with an explicit reason; the sequence is not silently truncated and folded; other tools continue; dossier reflects missing structural evidence. | status=supported, evidence_score=0.875, conflicts=0, identity_status=resolved_hint | ✅ |
| C: UniProt no-match on a supplied accession | uniprot.get_entry returns a 404-shaped ERROR (invalid/unknown accession) | Identity stays UNRESOLVED; no accession is invented; downstream evidence requiring identity is correctly SKIPPED, not fabricated; final status reflects insufficient evidence. | status=insufficient_evidence, evidence_score=0.125, conflicts=0, identity_status=unresolved | ✅ |
| D: Conflicting evidence between independent sources | uniprot resolves to 'Hemagglutinin' while iedb's records name 'Spike glycoprotein' for the same accession | A conflict object is created and surfaced; confidence is not allowed to paper over it; final status becomes CONFLICTING; the system does not silently pick a preferred side. | status=conflicting, evidence_score=0.833, conflicts=1, identity_status=resolved_hint | ✅ |
| E: Valid but insufficient evidence | none — no accession_hint given, so only a real predicted structure is ever established | The agent abstains: final status = INSUFFICIENT_EVIDENCE; the dossier explains what's missing; no unsupported identity/epitope conclusion is produced despite a genuinely valid structure prediction existing. | status=insufficient_evidence, evidence_score=0.167, conflicts=0, identity_status=unresolved | ✅ |
| F: Malformed (wrong-shape) API responses | uniprot.get_entry and europe_pmc.search both return a 200 OK with a non-dict body | The parser rejects the malformed payload safely (no crash); a structured failure is recorded; no fabricated fallback evidence is produced; other tools continue; final result reflects the missing source. | status=insufficient_evidence, evidence_score=0.25, conflicts=0, identity_status=unresolved | ✅ |
| G: Literature that may concern a homolog, not the exact sequence | none — realistic name-matched Europe PMC results, which can never be proven to be about this exact sequence | Literature is retained as useful context but every record is labeled INDIRECT; it is never counted as exact-sequence (DIRECT) evidence; the dossier preserves that distinction. | status=supported, evidence_score=1.0, conflicts=0, identity_status=resolved_hint | ✅ |
| H: One entire tool unavailable | iedb.search_epitopes_by_source_accession always fails (connection refused) | The failure is recorded; independent tools (uniprot, esm_atlas, europe_pmc) continue unaffected; no fabricated epitope evidence is produced; the final evidence score/status reflects the missing modality. | status=supported, evidence_score=0.875, conflicts=0, identity_status=resolved_hint | ✅ |

## Failure analysis

No scenario or benchmark case with a defined expectation failed on this run.

## Limitations

- curie does not perform sequence-to-accession identity resolution; cases/scenarios supplying accession_hint are excluded from identity-resolution accuracy scoring (identity_supplied is not identity_resolved). See docs/LIMITATIONS.md.
- evidence_score / confidence_class are internal, deterministic evidence-support scores, not calibrated probabilities of biological truth. See curie/agent/nodes/confidence_gate.py.
- end_to_end_success only scores cases/scenarios with a defined expected final status; 5 of 6 scientific-benchmark cases leave it 'not_evaluated' because their exact outcome depends on live API text this evaluation does not control in advance (see curie/evaluation/datasets/README.md).
- A previously undetected bug (verify_identity_consistency assumed a UniProt *search* response shape but the real code path uses get_entry, a differently-shaped single record) meant the identity-consistency cross-check always returned UNVERIFIABLE on every real run prior to this evaluation phase. Found via fault-injection testing and fixed in curie/tools/evidence_verification.py; see docs/LIMITATIONS.md and the Phase 3 report for detail.
- The 6 scientific-benchmark proteins were deliberately chosen because they are well-characterized model antigens/viral targets with rich public UniProt/IEDB/literature coverage (see curie/evaluation/datasets/README.md) — a near-100% result here reflects correct behavior on well-documented proteins, not a claim that curie performs this well on obscure or sparsely-annotated ones, which this evaluation does not test.
- Once an accession_hint resolves via UniProt, curie/evaluation/reliability.py's score_run gives a confidence floor of ~0.625 (0.5 x agreement_rate=1.0 from the always-AGREE identity_resolved finding, plus >=0 tool_success_rate) — meaning a run with a resolved identity can currently degrade to PARTIALLY_SUPPORTED at worst, never abstain into INSUFFICIENT_EVIDENCE, no matter how many of the other three tools fail. Confirmed analytically and not exercised by any scenario here (Scenario E and the no-hint benchmark case both test the unresolved-identity path instead). This is the top scoring-logic risk carried into Phase 4.
