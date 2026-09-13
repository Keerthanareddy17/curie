"""Evidence adjudication node.

Responsibility: deterministic cross-checking of the evidence pool, and nothing
else. No LLM call happens here. Reuses the two rule-based checks from Phase 1
(`curie/tools/evidence_verification.py`, still covered by its own unit tests)
rather than re-deriving them, and adds one more identity-specific check. Each
check becomes a `Claim`; any claim the checks mark CONFLICT becomes an explicit
`EvidenceConflict`. The evidence_score comes from `curie.evaluation.reliability.
score_run`, unchanged from Phase 1 — a reproducible function of tool outcomes and
claim agreement, not an opinion.
"""

from __future__ import annotations

import time

from curie.agent.state import InvestigationState
from curie.evaluation.reliability import score_run
from curie.shared.logging import get_logger
from curie.shared.models import (
    AgreementLevel,
    Claim,
    EvidenceConflict,
    IdentityStatus,
    ToolResult,
    ToolStatus,
    TraceEvent,
    VerificationFinding,
)
from curie.tools.evidence_verification import (
    verify_identity_consistency,
    verify_structural_and_epitope_evidence_present,
)

logger = get_logger(__name__)

NODE_NAME = "evidence_adjudication"


def _last_result(tool_results: list[ToolResult], provider: str) -> ToolResult | None:
    for result in reversed(tool_results):
        if result.provider == provider:
            return result
    return None


def _evidence_ids_for_sources(state: InvestigationState, sources: list[str]) -> list[str]:
    return [record.evidence_id for record in state.evidence if record.source in sources]


def _finding_to_claim(finding: VerificationFinding, state: InvestigationState) -> Claim:
    return Claim(
        statement=finding.claim,
        supporting_evidence_ids=_evidence_ids_for_sources(state, finding.supporting_sources),
        conflicting_evidence_ids=_evidence_ids_for_sources(state, finding.conflicting_sources),
        agreement=finding.agreement,
        notes=finding.notes,
    )


def _identity_resolved_finding(state: InvestigationState) -> VerificationFinding:
    if state.identity_status == IdentityStatus.RESOLVED_HINT:
        return VerificationFinding(
            claim="Sequence identity was resolved",
            supporting_sources=["uniprot"],
            agreement=AgreementLevel.AGREE,
            notes=f"Resolved via accession hint against UniProt ({state.protein_name}).",
        )
    return VerificationFinding(
        claim="Sequence identity was resolved",
        agreement=AgreementLevel.UNVERIFIABLE,
        notes="No accession hint was supplied or it failed to resolve; "
        "curie does not perform sequence-homology search (see docs/LIMITATIONS.md).",
    )


def evidence_adjudication(state: InvestigationState) -> dict:
    start = time.perf_counter()

    esm_result = _last_result(state.tool_results, "esm_atlas")
    uniprot_result = _last_result(state.tool_results, "uniprot")
    iedb_result = _last_result(state.tool_results, "iedb")

    findings: list[VerificationFinding] = [_identity_resolved_finding(state)]
    if uniprot_result is not None and iedb_result is not None:
        findings.append(verify_identity_consistency(uniprot_result, iedb_result))
    if esm_result is not None and iedb_result is not None:
        findings.append(verify_structural_and_epitope_evidence_present(esm_result, iedb_result))

    claims = [_finding_to_claim(f, state) for f in findings]

    conflicts: list[EvidenceConflict] = []
    for claim in claims:
        if claim.agreement != AgreementLevel.CONFLICT:
            continue
        evidence_a = claim.conflicting_evidence_ids[0] if claim.conflicting_evidence_ids else "unknown"
        evidence_b = claim.conflicting_evidence_ids[1] if len(claim.conflicting_evidence_ids) > 1 else evidence_a
        conflicts.append(
            EvidenceConflict(
                claim=claim.statement,
                evidence_a=evidence_a,
                evidence_b=evidence_b,
                conflict_type="cross_source_disagreement",
                severity="high",
                resolved=False,
                notes=claim.notes,
            )
        )

    reliability = score_run(state.tool_results, findings)
    evidence_score = reliability.confidence_score

    missing_evidence: list[str] = []
    for result in state.tool_results:
        if result.status == ToolStatus.SKIPPED:
            missing_evidence.append(f"{result.provider}.{result.operation} skipped: {result.error}")
        elif result.status in (ToolStatus.ERROR, ToolStatus.TIMEOUT):
            missing_evidence.append(f"{result.provider}.{result.operation} failed: {result.error}")
    if state.identity_status == IdentityStatus.UNRESOLVED:
        missing_evidence.append(
            "Sequence identity is unresolved; epitope and literature evidence "
            "(if present) are gated on it and structural evidence alone cannot "
            "confirm what this protein is."
        )

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "evidence_adjudication",
        run_id=state.run_id,
        evidence_score=evidence_score,
        conflicts=len(conflicts),
        claims=len(claims),
    )

    trace = TraceEvent(
        run_id=state.run_id,
        node=NODE_NAME,
        duration_ms=duration_ms,
        status="ok",
        input_summary=f"{len(state.evidence)} evidence record(s), {len(state.tool_results)} tool result(s)",
        output_summary=f"{len(claims)} claim(s), {len(conflicts)} conflict(s)",
        evidence_count=len(state.evidence),
        evidence_score=evidence_score,
    )

    return {
        "claims": claims,
        "conflicts": conflicts,
        "evidence_score": evidence_score,
        "missing_evidence": missing_evidence,
        "trace": [trace],
    }
