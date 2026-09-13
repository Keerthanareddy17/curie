"""Thin compatibility shim.

The real evaluation package lives at `curie/evaluation/` — a real,
already-importable subpackage of the installed `curie` package, not a second
top-level namespace. This directory exists only so the literal command
`python -m evaluation.runner` works from the repo root; see this package's
`runner.py` and `../curie/evaluation/README.md` for the rationale.
"""
