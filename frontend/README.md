# frontend/

No new frontend has been built for curie yet — this phase intentionally scoped frontend work
to zero, per the plan (agent + tooling first, UI later).

## `legacy/`


- `Molecular3DVisualizer.tsx` — a working React + 3Dmol.js structure viewer. It makes a real
  client-side call to the public ESM Atlas ESMFold API
  (`POST https://api.esmatlas.com/foldSequence/v1/pdb/`) and falls back to a synthetically
  generated alpha-helix/double-helix PDB when the API or WebGL isn't available. This is real,
  reusable visualization code, kept intentionally rather than discarded.
- `esmfold-demo.pdb` — a demo structure file the viewer can load without a network call.

These are not wired into a build yet. When curie grows a frontend, this component is the
intended starting point for structure visualization rather than something to rebuild from
scratch — everything else in the original UI (candidate ranking, epitope tables, the dossier
renderer) was driven by fabricated/LLM-narrated data (see `docs/ATTRIBUTION.md`) and was not
carried forward.
