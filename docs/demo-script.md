# curie — 2-minute demo script

## 1. Golden path (~45s)

Open the app, click **Run Golden Path**. Narrate as it runs:

"This is a real SARS-CoV-2 Spike RBD sequence. Gemini plans which evidence to
gather, then real calls go out to UniProt, ESM Atlas, IEDB, and Europe PMC —
you can see each one land in the agent trace. ESM Atlas's structure renders
live in 3D. Once evidence comes back, our deterministic adjudicator — not an
LLM — cross-checks sources, scores the evidence, and decides the status.
Gemini then writes a plain-language summary of what was already decided."

## 2. The reliability pitch (~60s)

"Here's the important part. You could look at this demo and say: 'Cool, Gemini
called four APIs.' That doesn't prove anything.

So we built an evaluation harness. We don't just test whether the final answer
sounds right. We test whether the agent did the right work, whether every claim
is grounded, whether sources agree, whether failures are recovered, and whether
it knows when to abstain.

We run the same system against known cases and deliberately injected failures —
timeouts, malformed responses, conflicting sources, oversized sequences. Eight
scenarios, all passing, all checked against the real graph, not a mock.

And here's the important architectural boundary: Gemini can plan the
investigation and explain the result. But it cannot change what our
deterministic evidence layer established. So when we inject a conflict, the
model doesn't get to talk its way out of it. The system reports the conflict."

Point at the **Evaluation benchmark** panel in the UI (already visible below the
main investigation) — those numbers come from `curie/evaluation/results/latest.json`,
regenerated live by `python -m curie.evaluation.runner --all`.

## 3. The killer failure demo (~15s)

Run the conflicting-evidence scenario from the terminal — no need to fake a live
API outage:

```bash
python -m curie.evaluation.runner --offline
```

Point at scenario **D: Conflicting evidence between independent sources**:
UniProt and IEDB are made to disagree about the protein's name. Nothing crashes.
The adjudicator detects the conflict, the confidence gate refuses to call it
`supported`, and the final status is `CONFLICTING`.

"Nothing crashed. The agent still failed the scientific question the way it
should — by refusing to be confident. And our evaluation caught that."
