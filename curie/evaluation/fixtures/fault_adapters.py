"""Deterministic fault-injecting stand-ins for the four real tool clients.

`ToolPatch` monkeypatches `UniProtClient.get_entry`, `IedbClient.search_
epitopes_by_source_accession`, `EuropePmcClient.search`, and `EsmAtlasClient.
fold_sequence` for the lifetime of a `with` block, then restores the originals
— usable from a plain script (curie/evaluation/scenarios/fault_scenarios.py,
which has no pytest fixture available) as well as from pytest tests. Only ever
used here and in tests; curie/tools/ and curie/agent/ never import this module,
so nothing in the production/demo path can accidentally run against a fixture.

Every scenario patches all four clients, defaulting the three not under test
to their real-shaped "everything is fine" fixture, so the one deliberately
faulty tool is the only variable — a scenario testing an ESM Atlas timeout
should not also accidentally be at the mercy of IEDB being slow that day.
"""

from __future__ import annotations

from collections.abc import Callable

from curie.evaluation.fixtures import tool_responses as fx
from curie.shared.models import ToolResult, ToolStatus
from curie.tools.esm_atlas import EsmAtlasClient
from curie.tools.europe_pmc import EuropePmcClient
from curie.tools.iedb import IedbClient
from curie.tools.uniprot import UniProtClient


def ok_uniprot() -> ToolResult:
    return ToolResult(
        provider="uniprot", operation="get_entry", status=ToolStatus.OK,
        latency_ms=5.0, data=fx.UNIPROT_OK,
    )


def ok_iedb() -> ToolResult:
    return ToolResult(
        provider="iedb", operation="search_epitopes_by_source_accession",
        status=ToolStatus.OK, latency_ms=5.0, data=fx.IEDB_OK,
    )


def ok_europe_pmc() -> ToolResult:
    return ToolResult(
        provider="europe_pmc", operation="search", status=ToolStatus.OK,
        latency_ms=5.0, data=fx.EUROPE_PMC_OK,
    )


def ok_esm() -> ToolResult:
    return ToolResult(
        provider="esm_atlas", operation="fold_sequence", status=ToolStatus.OK,
        latency_ms=5.0, data=fx.ESM_ATLAS_OK_PDB,
    )


def timeout_esm() -> ToolResult:
    return ToolResult(
        provider="esm_atlas", operation="fold_sequence", status=ToolStatus.TIMEOUT,
        latency_ms=60_000.0, error="injected fault: ESM Atlas timed out after 60s",
    )


def error_uniprot_no_match() -> ToolResult:
    return ToolResult(
        provider="uniprot", operation="get_entry", status=ToolStatus.ERROR,
        latency_ms=120.0,
        error="injected fault: 404 Client Error: Not Found (no UniProt match for this accession)",
    )


def conflicting_uniprot() -> ToolResult:
    return ToolResult(
        provider="uniprot", operation="get_entry", status=ToolStatus.OK,
        latency_ms=5.0, data=fx.UNIPROT_DIFFERENT_PROTEIN,
    )


def malformed_uniprot() -> ToolResult:
    return ToolResult(
        provider="uniprot", operation="get_entry", status=ToolStatus.OK,
        latency_ms=5.0, data=fx.MALFORMED_UNIPROT_PAYLOAD,
    )


def malformed_europe_pmc() -> ToolResult:
    return ToolResult(
        provider="europe_pmc", operation="search", status=ToolStatus.OK,
        latency_ms=5.0, data=fx.MALFORMED_EUROPE_PMC_PAYLOAD,
    )


def unavailable_iedb() -> ToolResult:
    return ToolResult(
        provider="iedb", operation="search_epitopes_by_source_accession",
        status=ToolStatus.ERROR, latency_ms=15.0,
        error="injected fault: connection refused (IEDB unavailable)",
    )


def error_esm_failed() -> ToolResult:
    return ToolResult(
        provider="esm_atlas", operation="fold_sequence", status=ToolStatus.ERROR,
        latency_ms=200.0, error="injected fault: 500 Internal Server Error",
    )


def error_europe_pmc() -> ToolResult:
    return ToolResult(
        provider="europe_pmc", operation="search", status=ToolStatus.ERROR,
        latency_ms=200.0, error="injected fault: 503 Service Unavailable",
    )


def empty_iedb() -> ToolResult:
    return ToolResult(
        provider="iedb", operation="search_epitopes_by_source_accession",
        status=ToolStatus.OK, latency_ms=5.0, data=fx.IEDB_EMPTY,
    )


_DEFAULTS: dict[str, Callable[[], ToolResult]] = {
    "uniprot": ok_uniprot,
    "iedb": ok_iedb,
    "europe_pmc": ok_europe_pmc,
    "esm_atlas": ok_esm,
}

_TARGETS = {
    "uniprot": (UniProtClient, "get_entry"),
    "iedb": (IedbClient, "search_epitopes_by_source_accession"),
    "europe_pmc": (EuropePmcClient, "search"),
    "esm_atlas": (EsmAtlasClient, "fold_sequence"),
}


class ToolPatch:
    """Context manager: patch some/all of the 4 tool clients, restore on exit.

    Unspecified tools default to their "everything is fine" fixture:

        with ToolPatch(esm_atlas=timeout_esm):
            state = await run_investigation(sequence, accession_hint="P0DTC2")

    only ESM Atlas is faulty above; UniProt/IEDB/Europe PMC behave normally.
    """

    def __init__(self, **overrides: Callable[[], ToolResult]):
        unknown = set(overrides) - set(_DEFAULTS)
        if unknown:
            raise ValueError(f"unknown tool name(s) for ToolPatch: {unknown}")
        self._fns = {**_DEFAULTS, **overrides}
        self._originals: dict[str, tuple[type, str, Callable]] = {}

    def __enter__(self) -> "ToolPatch":
        for key, (cls, method_name) in _TARGETS.items():
            self._originals[key] = (cls, method_name, getattr(cls, method_name))
            fn = self._fns[key]

            async def _patched(self_, *args, __fn=fn, **kwargs) -> ToolResult:
                return __fn()

            setattr(cls, method_name, _patched)
        return self

    def __exit__(self, *exc_info) -> bool:
        for cls, method_name, original in self._originals.values():
            setattr(cls, method_name, original)
        return False
