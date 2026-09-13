# Fault-injection fixtures

`tool_responses.py` holds canned response payloads; `fault_adapters.py`
monkeypatches the four real tool client classes (`UniProtClient`,
`IedbClient`, `EuropePmcClient`, `EsmAtlasClient`) to return them for the
duration of a single fault-injection scenario, then restores the originals.

**These are the only fabricated external-API response shapes in this
repository outside of Phase 1/2's own test fixtures (`tests/fixtures/`).**
Nothing under `curie/tools/` or `curie/agent/` imports this package — the
demo path always calls the live APIs. Only `curie/evaluation/scenarios/` and
this project's own tests import it.

## Why fixtures, not real API failures

The spec is explicit: "Do NOT rely on real external services breaking." A
reliability benchmark that only passes when a third party happens to be down
that day is not reproducible. Every fault here — timeout, malformed payload,
no-match, service-unavailable, conflicting sources — is constructed once,
checked in, and reproduced identically on every run.

## `ToolPatch`

```python
from curie.evaluation.fixtures.fault_adapters import ToolPatch, timeout_esm

with ToolPatch(esm_atlas=timeout_esm):
    state = await run_investigation(sequence, accession_hint="P0DTC2")
```

Any tool not named in the constructor defaults to its "everything is fine"
fixture, so a scenario testing one fault doesn't accidentally also depend on
the other three tools' fixture data being realistic — it isolates the one
variable under test.
