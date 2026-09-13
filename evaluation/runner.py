"""Compatibility entrypoint: `python -m evaluation.runner`.

Delegates entirely to curie.evaluation.runner, the real implementation
(nested under the installed `curie` package rather than a second top-level
namespace — see evaluation/__init__.py and curie/evaluation/README.md).
"""

from curie.evaluation.runner import main

if __name__ == "__main__":
    raise SystemExit(main())
