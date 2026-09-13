"""Deterministic fault-injection scenarios — the "behavioral reliability
benchmark" half of Phase 3 (as opposed to the "scientific/evidence benchmark"
in curie/evaluation/benchmark.py, which runs real cases against live APIs).

Named `fault_scenarios.py` rather than `reliability.py` deliberately: `curie/
evaluation/reliability.py` already exists (Phase 2's deterministic evidence
scorer, used live by the production graph) and giving this module the same
name would be confusing, not equivalent.

Every scenario here:
1. Builds a `ToolPatch` (curie/evaluation/fixtures/fault_adapters.py) that
   forces exactly one class of fault, defaulting every other tool to its
   realistic "everything is fine" fixture.
2. Runs the REAL, unmodified graph (`curie.agent.graph.run_investigation`)
   against that patched environment — the graph itself is never mocked, only
   the tool clients it calls.
3. Asserts a short list of specific, named behaviors the spec requires for
   that fault, and reports each as a pass/fail `ScenarioCheck`.

A scenario is marked `crashed=True` if `run_investigation` raised — that is
itself a scenario failure (safe degradation means the graph must never crash,
regardless of what a tool returns).
"""

from __future__ import annotations

import os
from contextlib import contextmanager

from curie.agent.graph import run_investigation
from curie.agent.state import InvestigationState
from curie.evaluation.fixtures.fault_adapters import (
    ToolPatch,
    conflicting_uniprot,
    error_esm_failed,
    error_uniprot_no_match,
    malformed_europe_pmc,
    malformed_uniprot,
    ok_esm,
    unavailable_iedb,
)
from curie.evaluation.models import ScenarioCheck, ScenarioResult
from curie.shared.models import (
    AgreementLevel,
    Directness,
    EvidenceType,
    IdentityStatus,
    InvestigationStatus,
    ToolStatus,
)

RBD_SEQUENCE = (
    "RVQPTESIVRFPNITNLCPFGEVFNATRFASVYAWNRKRISNCVADYSVLYNSASFSTFKCYGVSPTKLND"
    "LCFTNVYADSFVIRGDEVRQIAPGQTGKIADYNYKLPDDFTGCVIAWNSNNLDSKVGGNYNYLYRLFRKSN"
    "LKPFERDISTEIYQAGSTPCNGVEGFNCYFPLQSYGFQPTNGVGYQPYRVVVLSFELLHAPATVCGPKKST"
    "NLVKNKCVNF"
)  # SARS-CoV-2 Spike RBD, residues 319-541 of P0DTC2 — same fragment as the
# scientific benchmark's dataset cases; reused here purely as a realistic,
# fold-able (<=400 aa) input, not for its identity (which every scenario
# below controls explicitly via its ToolPatch).


def _find(results, provider: str):
    return next((r for r in results if r.provider == provider), None)


@contextmanager
def _no_gemini():
    """Force the deterministic (no-Gemini) path for the duration of one
    scenario, regardless of whether a real GEMINI_API_KEY happens to be
    configured in this environment's .env for the live demo. These 8
    scenarios test curie's bio-tool fault handling (timeouts, malformed
    responses, conflicts, ...) — a property that must hold the same way
    whether or not Gemini happens to be configured today, so it is held
    fixed here rather than left to vary with the ambient environment.
    Gemini's own fault-handling gets its own dedicated tests."""
    previous = os.environ.get("GEMINI_API_KEY")
    os.environ["GEMINI_API_KEY"] = ""
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("GEMINI_API_KEY", None)
        else:
            os.environ["GEMINI_API_KEY"] = previous


async def _run(sequence: str, accession_hint: str | None, patch: ToolPatch):
    with _no_gemini(), patch:
        return await run_investigation(sequence, accession_hint=accession_hint)


def _result(
    scenario_id: str,
    title: str,
    injected_fault: str,
    expected_behavior: str,
    checks: list[ScenarioCheck],
    state: InvestigationState | None,
    crashed: bool = False,
    tags: list[str] | None = None,
) -> ScenarioResult:
    passed = not crashed and all(c.passed for c in checks)
    if crashed:
        actual = "The graph raised an unhandled exception instead of degrading gracefully."
    elif state is None:
        actual = "not run"
    else:
        actual = (
            f"status={state.status.value}, evidence_score={state.evidence_score}, "
            f"conflicts={len(state.conflicts)}, identity_status={state.identity_status.value}"
        )
    return ScenarioResult(
        scenario_id=scenario_id,
        title=title,
        injected_fault=injected_fault,
        expected_behavior=expected_behavior,
        actual_behavior=actual,
        passed=passed,
        crashed=crashed,
        checks=checks,
        run_id=state.run_id if state else None,
        tags=tags or [],
        conflict_detected=bool(state and state.conflicts),
        final_status=state.status.value if state else None,
        identity_status=state.identity_status.value if state else None,
    )


async def scenario_a_esm_timeout() -> ScenarioResult:
    from curie.evaluation.fixtures.fault_adapters import timeout_esm

    scenario_id, title = "A", "ESM Atlas timeout"
    injected = "esm_atlas.fold_sequence times out"
    expected = (
        "Timeout recorded as ToolStatus.TIMEOUT; no fake structure generated; "
        "trace contains the failure; independent evidence collection continues; "
        "dossier states structural evidence is unavailable."
    )
    try:
        state = await _run(RBD_SEQUENCE, "P0DTC2", ToolPatch(esm_atlas=timeout_esm))
    except Exception as exc:  # noqa: BLE001
        return _result(scenario_id, title, injected, expected, [
            ScenarioCheck(description="graph completes without raising", passed=False, detail=str(exc))
        ], None, crashed=True)

    esm_result = _find(state.tool_results, "esm_atlas")
    checks = [
        ScenarioCheck(
            description="esm_atlas ToolResult status is TIMEOUT",
            passed=esm_result is not None and esm_result.status == ToolStatus.TIMEOUT,
            detail=str(esm_result.status if esm_result else None),
        ),
        ScenarioCheck(
            description="no structure data was fabricated on timeout",
            passed=esm_result is not None and esm_result.data is None,
        ),
        ScenarioCheck(
            description="trace contains a non-ok structure_prediction event",
            passed=any(t.node == "structure_prediction" and t.status != "ok" for t in state.trace),
        ),
        ScenarioCheck(
            description="independent tools (uniprot, iedb, europe_pmc) still ran and succeeded",
            passed=all(
                (r := _find(state.tool_results, p)) is not None and r.status == ToolStatus.OK
                for p in ("uniprot", "iedb", "europe_pmc")
            ),
        ),
        ScenarioCheck(
            description="dossier records no predicted-structure evidence",
            passed=state.dossier is not None and state.dossier.structural_evidence == [],
        ),
    ]
    return _result(scenario_id, title, injected, expected, checks, state, tags=["tool_recovery", "conflict_not_expected"])


async def scenario_b_oversized_sequence() -> ScenarioResult:
    scenario_id, title = "B", "Sequence exceeds ESM Atlas's fold-length limit"
    injected = "none (real code path) — a 450 aa sequence, over the 400 aa limit"
    expected = (
        "ESM Atlas is SKIPPED with an explicit reason; the sequence is not "
        "silently truncated and folded; other tools continue; dossier reflects "
        "missing structural evidence."
    )
    long_sequence = "M" * 450
    try:
        state = await _run(long_sequence, "P0DTC2", ToolPatch())
    except Exception as exc:  # noqa: BLE001
        return _result(scenario_id, title, injected, expected, [
            ScenarioCheck(description="graph completes without raising", passed=False, detail=str(exc))
        ], None, crashed=True)

    esm_result = _find(state.tool_results, "esm_atlas")
    checks = [
        ScenarioCheck(
            description="esm_atlas ToolResult status is SKIPPED",
            passed=esm_result is not None and esm_result.status == ToolStatus.SKIPPED,
        ),
        ScenarioCheck(
            description="skip reason explicitly mentions the length limit",
            passed=bool(esm_result and esm_result.error and "exceeds" in esm_result.error),
            detail=esm_result.error if esm_result else "",
        ),
        ScenarioCheck(
            description="sequence was not silently truncated before evaluation",
            passed=len(state.normalized_sequence) == len(long_sequence),
            detail=f"normalized_length={len(state.normalized_sequence)}, input_length={len(long_sequence)}",
        ),
        ScenarioCheck(
            description="other tools (uniprot, iedb, europe_pmc) still ran and succeeded",
            passed=all(
                (r := _find(state.tool_results, p)) is not None and r.status == ToolStatus.OK
                for p in ("uniprot", "iedb", "europe_pmc")
            ),
        ),
        ScenarioCheck(
            description="dossier records no predicted-structure evidence",
            passed=state.dossier is not None and state.dossier.structural_evidence == [],
        ),
    ]
    return _result(scenario_id, title, injected, expected, checks, state, tags=["conflict_not_expected"])


async def scenario_c_uniprot_no_match() -> ScenarioResult:
    scenario_id, title = "C", "UniProt no-match on a supplied accession"
    injected = "uniprot.get_entry returns a 404-shaped ERROR (invalid/unknown accession)"
    expected = (
        "Identity stays UNRESOLVED; no accession is invented; downstream "
        "evidence requiring identity is correctly SKIPPED, not fabricated; "
        "final status reflects insufficient evidence."
    )
    try:
        state = await _run(RBD_SEQUENCE, "BOGUS00000", ToolPatch(uniprot=error_uniprot_no_match))
    except Exception as exc:  # noqa: BLE001
        return _result(scenario_id, title, injected, expected, [
            ScenarioCheck(description="graph completes without raising", passed=False, detail=str(exc))
        ], None, crashed=True)

    iedb_result = _find(state.tool_results, "iedb")
    pmc_result = _find(state.tool_results, "europe_pmc")
    checks = [
        ScenarioCheck(
            description="identity_status is UNRESOLVED",
            passed=state.identity_status == IdentityStatus.UNRESOLVED,
        ),
        ScenarioCheck(
            description="no candidate protein was fabricated",
            passed=state.candidate_proteins == [],
        ),
        ScenarioCheck(
            description="IEDB query correctly SKIPPED (no resolved accession)",
            passed=iedb_result is not None and iedb_result.status == ToolStatus.SKIPPED,
        ),
        ScenarioCheck(
            description="Europe PMC query correctly SKIPPED (no resolved protein name)",
            passed=pmc_result is not None and pmc_result.status == ToolStatus.SKIPPED,
        ),
        ScenarioCheck(
            description="final status reflects insufficient evidence",
            passed=state.status == InvestigationStatus.INSUFFICIENT_EVIDENCE,
            detail=state.status.value,
        ),
        ScenarioCheck(
            description="dossier identity_result honestly says UNRESOLVED",
            passed=state.dossier is not None and "UNRESOLVED" in state.dossier.identity_result,
        ),
    ]
    return _result(scenario_id, title, injected, expected, checks, state, tags=["tool_recovery", "abstention_expected", "conflict_not_expected"])


async def scenario_d_conflicting_evidence() -> ScenarioResult:
    scenario_id, title = "D", "Conflicting evidence between independent sources"
    injected = "uniprot resolves to 'Hemagglutinin' while iedb's records name 'Spike glycoprotein' for the same accession"
    expected = (
        "A conflict object is created and surfaced; confidence is not allowed "
        "to paper over it; final status becomes CONFLICTING; the system does "
        "not silently pick a preferred side."
    )
    try:
        state = await _run(RBD_SEQUENCE, "P0DTC2", ToolPatch(uniprot=conflicting_uniprot))
    except Exception as exc:  # noqa: BLE001
        return _result(scenario_id, title, injected, expected, [
            ScenarioCheck(description="graph completes without raising", passed=False, detail=str(exc))
        ], None, crashed=True)

    checks = [
        ScenarioCheck(
            description="at least one conflict was recorded",
            passed=len(state.conflicts) >= 1,
            detail=f"{len(state.conflicts)} conflict(s)",
        ),
        ScenarioCheck(
            description="at least one claim has agreement=CONFLICT",
            passed=any(c.agreement == AgreementLevel.CONFLICT for c in state.claims),
        ),
        ScenarioCheck(
            description="no conflict was silently marked resolved",
            passed=all(not c.resolved for c in state.conflicts),
        ),
        ScenarioCheck(
            description="final status is CONFLICTING",
            passed=state.status == InvestigationStatus.CONFLICTING,
            detail=state.status.value,
        ),
        ScenarioCheck(
            description="dossier surfaces the conflict rather than hiding it",
            passed=state.dossier is not None and len(state.dossier.conflicts) >= 1,
        ),
    ]
    return _result(scenario_id, title, injected, expected, checks, state, tags=["conflict_expected"])


async def scenario_e_insufficient_evidence() -> ScenarioResult:
    scenario_id, title = "E", "Valid but insufficient evidence"
    injected = "none — no accession_hint given, so only a real predicted structure is ever established"
    expected = (
        "The agent abstains: final status = INSUFFICIENT_EVIDENCE; the dossier "
        "explains what's missing; no unsupported identity/epitope conclusion "
        "is produced despite a genuinely valid structure prediction existing."
    )
    try:
        state = await _run(RBD_SEQUENCE, None, ToolPatch())
    except Exception as exc:  # noqa: BLE001
        return _result(scenario_id, title, injected, expected, [
            ScenarioCheck(description="graph completes without raising", passed=False, detail=str(exc))
        ], None, crashed=True)

    esm_result = _find(state.tool_results, "esm_atlas")
    checks = [
        ScenarioCheck(
            description="a genuinely valid structure prediction exists",
            passed=esm_result is not None and esm_result.status == ToolStatus.OK,
        ),
        ScenarioCheck(
            description="identity remains UNRESOLVED (never attempted, no hint given)",
            passed=state.identity_status == IdentityStatus.UNRESOLVED,
        ),
        ScenarioCheck(
            description="final status is INSUFFICIENT_EVIDENCE (abstention)",
            passed=state.status == InvestigationStatus.INSUFFICIENT_EVIDENCE,
            detail=state.status.value,
        ),
        ScenarioCheck(
            description="dossier lists specific missing evidence",
            passed=state.dossier is not None and len(state.dossier.missing_evidence) >= 1,
        ),
        ScenarioCheck(
            description="no identity or epitope conclusion is asserted",
            passed=state.dossier is not None and "UNRESOLVED" in state.dossier.identity_result,
        ),
    ]
    return _result(scenario_id, title, injected, expected, checks, state, tags=["abstention_expected", "conflict_not_expected"])


async def scenario_f_malformed_response() -> ScenarioResult:
    scenario_id, title = "F", "Malformed (wrong-shape) API responses"
    injected = "uniprot.get_entry and europe_pmc.search both return a 200 OK with a non-dict body"
    expected = (
        "The parser rejects the malformed payload safely (no crash); a "
        "structured failure is recorded; no fabricated fallback evidence is "
        "produced; other tools continue; final result reflects the missing source."
    )
    try:
        state_uniprot = await _run(RBD_SEQUENCE, "P0DTC2", ToolPatch(uniprot=malformed_uniprot))
    except Exception as exc:  # noqa: BLE001
        return _result(scenario_id, title, injected, expected, [
            ScenarioCheck(description="graph survives malformed uniprot payload", passed=False, detail=str(exc))
        ], None, crashed=True)

    try:
        state_pmc = await _run(
            RBD_SEQUENCE, "P0DTC2", ToolPatch(europe_pmc=malformed_europe_pmc)
        )
    except Exception as exc:  # noqa: BLE001
        return _result(scenario_id, title, injected, expected, [
            ScenarioCheck(description="graph survives malformed europe_pmc payload", passed=False, detail=str(exc))
        ], None, crashed=True)

    esm_result = _find(state_uniprot.tool_results, "esm_atlas")
    checks = [
        ScenarioCheck(
            description="malformed uniprot payload does not crash the graph",
            passed=True,  # reaching here means it didn't raise
        ),
        ScenarioCheck(
            description="malformed uniprot payload leaves identity UNRESOLVED, not guessed",
            passed=state_uniprot.identity_status == IdentityStatus.UNRESOLVED,
        ),
        ScenarioCheck(
            description="independent esm_atlas still succeeds despite malformed uniprot data",
            passed=esm_result is not None and esm_result.status == ToolStatus.OK,
        ),
        ScenarioCheck(
            description="malformed europe_pmc payload does not crash the graph",
            passed=True,
        ),
        ScenarioCheck(
            description="malformed europe_pmc payload is recorded as absence-of-evidence, not fabricated literature",
            passed=any(
                e.source == "europe_pmc" and e.evidence_type == EvidenceType.ABSENCE_OF_EVIDENCE
                for e in state_pmc.evidence
            ),
        ),
    ]
    return _result(scenario_id, title, injected, expected, checks, state_uniprot, tags=["tool_recovery", "conflict_not_expected"])


async def scenario_g_homolog_literature() -> ScenarioResult:
    scenario_id, title = "G", "Literature that may concern a homolog, not the exact sequence"
    injected = "none — realistic name-matched Europe PMC results, which can never be proven to be about this exact sequence"
    expected = (
        "Literature is retained as useful context but every record is labeled "
        "INDIRECT; it is never counted as exact-sequence (DIRECT) evidence; "
        "the dossier preserves that distinction."
    )
    try:
        state = await _run(RBD_SEQUENCE, "P0DTC2", ToolPatch())
    except Exception as exc:  # noqa: BLE001
        return _result(scenario_id, title, injected, expected, [
            ScenarioCheck(description="graph completes without raising", passed=False, detail=str(exc))
        ], None, crashed=True)

    literature = [e for e in state.evidence if e.evidence_type == EvidenceType.LITERATURE]
    checks = [
        ScenarioCheck(
            description="literature evidence was retained",
            passed=len(literature) >= 1,
        ),
        ScenarioCheck(
            description="every literature record is marked INDIRECT, never DIRECT",
            passed=len(literature) >= 1 and all(e.directness == Directness.INDIRECT for e in literature),
        ),
        ScenarioCheck(
            description="dossier's literature_evidence references those same (indirect) records",
            passed=state.dossier is not None and len(state.dossier.literature_evidence) == len(literature),
        ),
    ]
    return _result(scenario_id, title, injected, expected, checks, state, tags=["conflict_not_expected"])


async def scenario_h_tool_unavailable() -> ScenarioResult:
    scenario_id, title = "H", "One entire tool unavailable"
    injected = "iedb.search_epitopes_by_source_accession always fails (connection refused)"
    expected = (
        "The failure is recorded; independent tools (uniprot, esm_atlas, "
        "europe_pmc) continue unaffected; no fabricated epitope evidence is "
        "produced; the final evidence score/status reflects the missing modality."
    )
    try:
        state = await _run(RBD_SEQUENCE, "P0DTC2", ToolPatch(iedb=unavailable_iedb))
    except Exception as exc:  # noqa: BLE001
        return _result(scenario_id, title, injected, expected, [
            ScenarioCheck(description="graph completes without raising", passed=False, detail=str(exc))
        ], None, crashed=True)

    iedb_result = _find(state.tool_results, "iedb")
    checks = [
        ScenarioCheck(
            description="iedb ToolResult status is ERROR",
            passed=iedb_result is not None and iedb_result.status == ToolStatus.ERROR,
        ),
        ScenarioCheck(
            description="identity still resolves independently of IEDB",
            passed=state.identity_status == IdentityStatus.RESOLVED_HINT,
        ),
        ScenarioCheck(
            description="esm_atlas and europe_pmc still ran and succeeded",
            passed=all(
                (r := _find(state.tool_results, p)) is not None and r.status == ToolStatus.OK
                for p in ("esm_atlas", "europe_pmc")
            ),
        ),
        ScenarioCheck(
            description="dossier reaches a real (non-crashed) final status",
            passed=state.dossier is not None,
        ),
        ScenarioCheck(
            description="evidence_score reflects the missing modality (< a fully-successful run's 1.0)",
            passed=(state.evidence_score or 0.0) < 1.0,
            detail=str(state.evidence_score),
        ),
        ScenarioCheck(
            description="missing_evidence mentions the iedb failure",
            passed=any("iedb" in m for m in state.missing_evidence),
        ),
    ]
    return _result(scenario_id, title, injected, expected, checks, state, tags=["tool_recovery", "conflict_not_expected"])


SCENARIOS = [
    scenario_a_esm_timeout,
    scenario_b_oversized_sequence,
    scenario_c_uniprot_no_match,
    scenario_d_conflicting_evidence,
    scenario_e_insufficient_evidence,
    scenario_f_malformed_response,
    scenario_g_homolog_literature,
    scenario_h_tool_unavailable,
]


async def run_all_scenarios() -> list[ScenarioResult]:
    return [await scenario() for scenario in SCENARIOS]
