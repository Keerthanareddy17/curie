"""curie's CLI.

`python -m curie serve`   — run the FastAPI app (health + investigate endpoints).
`python -m curie health`  — print a liveness check without starting a server.
`python -m curie run SEQ` — run the investigation graph on a sequence and print
                             the resulting state as JSON.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

import curie
from curie.shared.config import get_settings
from curie.shared.logging import configure_logging, get_logger


def _cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    settings = get_settings()
    uvicorn.run("curie.backend.api.app:app", host=settings.host, port=settings.port)
    return 0


def _cmd_health(_args: argparse.Namespace) -> int:
    print(json.dumps({"status": "ok", "version": curie.__version__}))
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    from curie.agent.graph import run_investigation

    async def _run() -> None:
        state = await run_investigation(args.sequence, accession_hint=args.accession_hint)
        print(state.model_dump_json(indent=2))

    asyncio.run(_run())
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    """Run one investigation and print the concise golden-path report."""
    from curie.agent.graph import run_investigation
    from curie.shared.models import ToolStatus

    async def _run() -> None:
        state = await run_investigation(args.sequence, accession_hint=args.accession_hint)

        def tool_verdict(provider: str) -> str:
            results = [r for r in state.tool_results if r.provider == provider]
            if not results:
                return "NOT CALLED"
            result = results[-1]
            if result.status == ToolStatus.OK:
                return "PASS"
            if result.status == ToolStatus.SKIPPED:
                return f"SKIPPED ({result.error})"
            return f"FAIL ({result.status.value}: {result.error})"

        print(f"Run ID: {state.run_id}")
        print(f"Sequence length: {len(state.raw_sequence)}")
        print(f"Sequence type: {state.sequence_type.value}")
        print()
        print("Tools:")
        for provider in ("uniprot", "iedb", "europe_pmc", "esm_atlas"):
            print(f"  {provider}: {tool_verdict(provider)}")
        print()
        print(f"Evidence records: {len(state.evidence)}")
        print(f"Conflicts: {len(state.conflicts)}")
        print(f"Evidence score: {state.evidence_score}")
        print(f"Final status: {state.status.value}")

    asyncio.run(_run())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="curie")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve_parser = subparsers.add_parser("serve", help="run the curie API server")
    serve_parser.set_defaults(func=_cmd_serve)

    health_parser = subparsers.add_parser("health", help="print a liveness check and exit")
    health_parser.set_defaults(func=_cmd_health)

    run_parser = subparsers.add_parser("run", help="run the investigation graph on one sequence")
    run_parser.add_argument("sequence", help="raw protein or DNA/RNA sequence (FASTA header ok)")
    run_parser.add_argument(
        "--accession-hint",
        dest="accession_hint",
        default=None,
        help="known UniProt accession for this sequence, e.g. P0DTC2",
    )
    run_parser.set_defaults(func=_cmd_run)

    report_parser = subparsers.add_parser(
        "report", help="run one investigation and print the concise golden-path report"
    )
    report_parser.add_argument("sequence", help="raw protein or DNA/RNA sequence (FASTA header ok)")
    report_parser.add_argument(
        "--accession-hint",
        dest="accession_hint",
        default=None,
        help="known UniProt accession for this sequence, e.g. P0DTC2",
    )
    report_parser.set_defaults(func=_cmd_report)

    return parser


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    configure_logging(level=settings.log_level, fmt=settings.log_format)
    get_logger(__name__).debug("cli_start", argv=argv or sys.argv[1:])

    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
