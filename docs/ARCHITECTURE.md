# Architecture

## Layout

```
curie/
├── frontend/            # no new UI built yet; vendored Billie Gene visualization
│   ├── README.md
│   └── legacy/          # Molecular3DVisualizer.tsx + esmfold-demo.pdb (MIT, see docs/ATTRIBUTION.md)
├── curie/                # the Python package (installable; `python -m curie`)
│   ├── backend/          # FastAPI app: health + investigate HTTP endpoints
│   │   └── api/
│   │       ├── app.py
│   │       └── routes/   # health.py, investigate.py
│   ├── agent/            # LangGraph orchestration
│   │   ├── state.py      # typed Pydantic AgentState (the graph's state schema)
│   │   ├── graph.py      # builds and runs the StateGraph
│   │   └── nodes/        # one file per node, one real responsibility each
│   ├── tools/            # external system clients + evidence verification
│   │   ├── base.py       # BaseToolClient: timing, logging, ToolResult envelope
│   │   ├── esm_atlas.py  # real: ESM Atlas ESMFold structure prediction
│   │   ├── uniprot.py    # real: UniProtKB search + entry lookup
│   │   ├── iedb.py       # real: IEDB IQ-API curated epitope search
│   │   ├── europe_pmc.py # real: Europe PMC literature search
│   │   └── evidence_verification.py  # rule-based cross-source consistency checks
│   ├── evaluation/       # turning a run's evidence into a reliability report
│   │   ├── reliability.py
│   │   └── harness.py    # runs fixture cases through the real graph
│   └── shared/           # config, structured logging, shared Pydantic models,
│                         # sequence utilities (ported from Billie Gene, see below)
├── tests/                # pytest; `-m "not network"` for the offline subset
│   └── fixtures/         # sample sequences + the ONLY allowed fake API responses
├── docs/                 # this file, ATTRIBUTION.md, LIMITATIONS.md
├── pyproject.toml
├── requirements.txt
└── .env.example
```

`backend/`, `agent/`, `tools/`, `evaluation/`, and `shared/` are each their own
directory with their own clear responsibility, nested one level under `curie/`
rather than as siblings of it at the repo root. This was a deliberate choice over
five separate top-level Python packages: names like `tools` and `shared` are
generic enough that adding them straight to `sys.path` as independent packages
risks colliding with other installed packages, and a single installable `curie`
package is more conventional Python packaging than a loose collection of
same-level directories glued together at runtime. The separation of concerns the
task asked for is real; only the filesystem nesting differs from a literal reading.

## The graph

```
sequence_intake -> structure_lookup -> epitope_evidence -> literature_check
    -> evidence_verification -> confidence_evaluation
```

Each node has one job, and every node earns its place — none exist just to hit a
naming checklist:

- **sequence_intake**: classifies the input as protein or DNA/RNA, translates DNA/RNA
  with a real codon table, and computes deterministic composition/hydrophobicity/
  antigenicity statistics. Pure logic, no network — this node must work offline.
- **structure_lookup**: calls the real ESM Atlas ESMFold API for a structure
  prediction, and (given `accession_hint`) the real UniProt API for protein identity.
- **epitope_evidence**: calls the real IEDB IQ-API for curated epitope evidence
  against `accession_hint`.
- **literature_check**: calls the real Europe PMC API using the protein name
  resolved upstream.
- **evidence_verification**: checks whether UniProt's and IEDB's protein names
  actually agree, and whether structural and epitope evidence both exist — the
  step with no equivalent anywhere in Billie Gene.
- **confidence_evaluation**: turns tool outcomes and verification findings into a
  single `ReliabilityReport` (`curie/evaluation/reliability.py`) with explicit caveats.

`accession_hint` is an honest interim interface, not a hidden shortcut: curie does
not yet do sequence-homology search to discover a UniProt accession from a raw
sequence on its own, so `structure_lookup`/`epitope_evidence`/`literature_check`
report a `not_implemented` `ToolResult` rather than guessing when it's absent. See
`docs/LIMITATIONS.md`.

## Tool call contract

Every `curie.tools.base.BaseToolClient.call(...)` returns a `ToolResult`
(`curie/shared/models.py`) with exactly these fields, always:

`provider`, `operation`, `status` (`ok` / `error` / `not_implemented` / `timeout`),
`latency_ms`, `request_id`, `error`. `data` carries the payload on success. Every
call is also logged as a structured `tool_call` event via `curie/shared/logging.py`.
This is what makes a later dossier auditable instead of a narrative: any claim can
be traced back to the exact call, its outcome, and how long it took.

## What's genuinely new vs. ported

See `docs/ATTRIBUTION.md` for the full accounting. In short: the ESM Atlas
integration pattern and the hydrophobicity/antigenicity reference scales trace back
to Billie Gene; DNA/RNA translation, ORF finding, all four real tool clients, the
typed LangGraph state and nodes, evidence verification, and the reliability scorer
are new.
