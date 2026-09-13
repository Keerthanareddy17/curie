# curie — evaluation summary for judges

**"Show how you know it works."** We don't grade whether Gemini's prose sounds right.
We run the same investigation through 6 real proteins (live APIs) and 8 injected
failure scenarios, and assert on the structured trace at every boundary: planner →
tool selection → tool execution → evidence → adjudication → confidence gate →
synthesis → dossier.

## Results (live run, `python -m curie.evaluation.runner --all`)

| Dimension | What we test | Result |
|---|---|---|
| Source retrieval | correct tool called/skipped per case | 100.0% |
| Provenance | every claim's source ID traces to a real call | 100.0% |
| Evidence grounding | claim → evidence record → source → identifier | 100.0% |
| Evidence-type correctness | curated vs. predicted vs. indirect labeled honestly | 100.0% |
| Cross-source consistency | independent sources agree where comparable | 100.0% |
| Conflict detection | injected cross-source disagreement caught | 100.0% |
| Abstention | insufficient evidence → system says so, doesn't guess | 100.0% |
| Tool recovery | injected timeouts/failures don't crash or fabricate | 100.0% |
| Unsupported claims | claims without grounding | 0.0% (lower is better) |
| End-to-end | full investigation reaches the expected final status | 100.0% |

6 scientific cases (real proteins, live UniProt/IEDB/Europe PMC/ESM Atlas) +
8 fault-injection scenarios (controlled fixtures, real unmodified graph). Numbers
regenerate from `curie/evaluation/results/latest.json` — nothing here is hand-typed.

### Behavioral scenarios

8 scenarios, all passing:

- ✓ ESM Atlas timeout → recorded, no fabricated structure, rest of investigation continues
- ✓ Oversized sequence (>400 aa) → ESM Atlas skipped explicitly, not silently truncated
- ✓ UniProt no-match → identity stays unresolved, dependent tools skip safely
- ✓ Conflicting evidence → conflict recorded, final status = CONFLICTING
- ✓ Insufficient evidence → system abstains (INSUFFICIENT_EVIDENCE), doesn't overclaim
- ✓ Malformed 200-OK responses → rejected safely, no fabricated fallback evidence
- ✓ Homolog literature → labeled INDIRECT, never counted as exact-sequence evidence
- ✓ Tool unavailable (IEDB down) → failure recorded, independent tools unaffected

## The key architectural guarantee

**Gemini cannot modify the evidence verdict.** `gemini_synthesis` runs strictly after
the deterministic `confidence_gate` node and can only write one field —
`ai_synthesis: str | None` — a narration string. It has no path to `evidence_score`,
`status`, `conflicts`, or `provenance`; that's enforced by the LangGraph state schema
(`curie/agent/state.py`), not by a prompt asking it nicely.
