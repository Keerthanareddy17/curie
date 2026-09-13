"""Deterministic, evidence-graph-level metrics for the scientific/evidence
benchmark (curie/evaluation/benchmark.py).

Every function here inspects `InvestigationState` — tool_results, evidence,
claims — never the dossier's prose. A dossier that "sounds right" is not
enough; these check whether the structured evidence graph actually supports
it. See curie/evaluation/README.md for how this half of Phase 3 relates to
the fault-scenario half (curie/evaluation/scenarios/fault_scenarios.py),
which covers behavioral-reliability metrics 6-8 and contributes to 7/10.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from curie.agent.state import InvestigationState
from curie.evaluation.models import BenchmarkCase, IdentityEvalClass
from curie.shared.models import (
    AgreementLevel,
    Directness,
    EvidenceLevel,
    EvidenceType,
    IdentityStatus,
    ToolStatus,
)

# The EvidenceLevel each source's own non-absence evidence must carry.
# Wrong here is exactly Metric 4's failure mode: predicted evidence dressed
# up as curated/observed, or vice versa.
EXPECTED_EVIDENCE_LEVEL = {
    "esm_atlas": EvidenceLevel.PREDICTED,
    "iedb": EvidenceLevel.CURATED,
    "uniprot": EvidenceLevel.CURATED,
    "europe_pmc": EvidenceLevel.CURATED,
}


@dataclass
class SourceCheckResult:
    source: str
    outcome: str  # "PASS" | "SKIPPED_CORRECTLY" | "FAILED" | "NOT_EVALUATED"
    detail: str = ""


@dataclass
class ProvenanceCheckResult:
    evidence_id: str
    valid: bool
    reasons: list[str] = field(default_factory=list)


@dataclass
class EvidenceTypeCorrectnessResult:
    evidence_id: str
    correct: bool
    reason: str = ""


@dataclass
class ClaimGroundingResult:
    claim_id: str
    grounded: bool
    reason: str = ""


@dataclass
class UnsupportedClaimResult:
    claim_id: str
    unsupported: bool
    reason: str = ""


@dataclass
class CaseEvaluation:
    case_id: str
    identity_eval_class: IdentityEvalClass
    source_checks: list[SourceCheckResult]
    provenance_checks: list[ProvenanceCheckResult]
    evidence_type_checks: list[EvidenceTypeCorrectnessResult]
    claim_grounding_checks: list[ClaimGroundingResult]
    unsupported_claim_checks: list[UnsupportedClaimResult]
    cross_source_consistency: str  # "agreement" | "disagreement" | "incomparable" | "insufficient_evidence"
    end_to_end_expected: str | None
    end_to_end_actual: str
    end_to_end_match: bool | None


def classify_identity(case: BenchmarkCase, state: InvestigationState) -> IdentityEvalClass:
    """Enforce the "no free information" rule mechanically, not just by convention.

    A case that supplied accession_hint is SUPPLIED, full stop — its outcome
    is never eligible to count toward identity-resolution accuracy, regardless
    of what state.identity_status ends up being.
    """
    if case.accession_hint:
        return IdentityEvalClass.SUPPLIED
    if case.expected.identity.status == "not_evaluated":
        return IdentityEvalClass.NOT_EVALUATED
    if state.identity_status == IdentityStatus.RESOLVED_HINT:
        # Not reachable by the current implementation without a hint (see
        # docs/LIMITATIONS.md) — kept so a future real resolver has somewhere
        # honest to report success, rather than this function assuming it's
        # impossible forever.
        return IdentityEvalClass.RESOLVED
    return IdentityEvalClass.UNRESOLVED


def check_sources(case: BenchmarkCase, state: InvestigationState) -> list[SourceCheckResult]:
    """Metric 1 ingredients: PASS / SKIPPED_CORRECTLY / FAILED / NOT_EVALUATED per source."""
    results = []
    for exp in case.expected.evidence_expectations:
        tool_result = next((r for r in state.tool_results if r.provider == exp.source), None)

        if exp.expect_status is None:
            results.append(SourceCheckResult(exp.source, "NOT_EVALUATED", "no expectation set for this case"))
            continue

        if tool_result is None:
            # e.g. uniprot is never even attempted without an accession hint.
            outcome = "SKIPPED_CORRECTLY" if not exp.should_be_called else "FAILED"
            results.append(SourceCheckResult(exp.source, outcome, "no ToolResult recorded (never called)"))
            continue

        if exp.expect_status == "ok":
            outcome = "PASS" if tool_result.status == ToolStatus.OK else "FAILED"
        elif exp.expect_status == "skipped":
            outcome = "SKIPPED_CORRECTLY" if tool_result.status == ToolStatus.SKIPPED else "FAILED"
        else:
            outcome = "PASS" if tool_result.status.value == exp.expect_status else "FAILED"

        results.append(SourceCheckResult(exp.source, outcome, f"actual_status={tool_result.status.value}"))
    return results


def _extract_pmc_ids(data) -> set[str]:
    if not isinstance(data, dict):
        return set()
    articles = data.get("resultList", {}).get("result", [])
    return {a.get("id") for a in articles if isinstance(a, dict) and a.get("id")}


def check_provenance(state: InvestigationState) -> list[ProvenanceCheckResult]:
    """Metric 2: every non-absence EvidenceRecord must have real, checkable provenance."""
    results = []
    for record in state.evidence:
        if record.evidence_type == EvidenceType.ABSENCE_OF_EVIDENCE:
            continue  # provenance requirements apply to claims of external support, not "we found nothing"

        reasons: list[str] = []
        if not record.source:
            reasons.append("missing source")
        if record.retrieved_at is None:
            reasons.append("missing retrieved_at")

        backing = next(
            (r for r in state.tool_results if r.provider == record.source and r.status == ToolStatus.OK),
            None,
        )
        if backing is None:
            reasons.append(f"no successful ToolResult from provider={record.source!r} backs this evidence")

        if record.evidence_type in (EvidenceType.CURATED_ANNOTATION, EvidenceType.LITERATURE) and not record.identifier:
            reasons.append("missing identifier for a source type that should carry one")

        if record.evidence_type == EvidenceType.LITERATURE and record.identifier and backing is not None:
            raw_ids = _extract_pmc_ids(backing.data)
            if raw_ids and record.identifier not in raw_ids:
                reasons.append(f"identifier {record.identifier!r} not found in the backing call's raw response")

        results.append(ProvenanceCheckResult(record.evidence_id, valid=not reasons, reasons=reasons))
    return results


def check_evidence_type_correctness(state: InvestigationState) -> list[EvidenceTypeCorrectnessResult]:
    """Metric 4: curated/predicted/experimental/indirect labels must be honest."""
    results = []
    for record in state.evidence:
        if record.evidence_type == EvidenceType.ABSENCE_OF_EVIDENCE:
            continue

        reasons: list[str] = []
        expected_level = EXPECTED_EVIDENCE_LEVEL.get(record.source)
        if expected_level is not None and record.evidence_level != expected_level:
            reasons.append(
                f"expected evidence_level={expected_level.value} for source={record.source}, "
                f"got {record.evidence_level.value}"
            )
        if record.evidence_type == EvidenceType.LITERATURE and record.directness != Directness.INDIRECT:
            reasons.append("literature evidence must be INDIRECT, never presented as exact-sequence evidence")
        if record.evidence_type == EvidenceType.PREDICTED_STRUCTURE and record.evidence_level != EvidenceLevel.PREDICTED:
            reasons.append("predicted structure must not be labeled anything but PREDICTED")
        if record.evidence_type == EvidenceType.EXPERIMENTAL_STRUCTURE and record.evidence_level != EvidenceLevel.OBSERVED:
            reasons.append("experimental structure must be labeled OBSERVED, not PREDICTED/CURATED")

        results.append(EvidenceTypeCorrectnessResult(record.evidence_id, correct=not reasons, reason="; ".join(reasons)))
    return results


def check_claim_grounding(state: InvestigationState) -> list[ClaimGroundingResult]:
    """Metric 3: does every claim trace back to real, provenance-valid evidence?

    A claim whose agreement is UNVERIFIABLE is vacuously grounded — it asserts
    nothing beyond "insufficient data," which is itself consistent with citing
    no evidence. AGREE/CONFLICT claims must cite at least one evidence_id, and
    every cited id must exist and pass provenance.
    """
    evidence_ids = {e.evidence_id for e in state.evidence}
    provenance_by_id = {p.evidence_id: p.valid for p in check_provenance(state)}

    results = []
    for claim in state.claims:
        cited = claim.supporting_evidence_ids + claim.conflicting_evidence_ids
        reasons: list[str] = []

        if claim.agreement in (AgreementLevel.AGREE, AgreementLevel.CONFLICT) and not cited:
            reasons.append(f"agreement={claim.agreement.value} but cites no evidence_ids")

        for eid in cited:
            if eid not in evidence_ids:
                reasons.append(f"cites nonexistent evidence_id {eid!r} (citation-shaped hallucination)")
            elif provenance_by_id.get(eid) is False:
                reasons.append(f"cites evidence_id {eid!r} which fails provenance validation")

        results.append(ClaimGroundingResult(claim.claim_id, grounded=not reasons, reason="; ".join(reasons)))
    return results


def check_unsupported_claims(state: InvestigationState) -> list[UnsupportedClaimResult]:
    """Metric 9: a claim is unsupported if it isn't grounded, or if evidence it
    cites mislabels its own type/directness (e.g. treats a homolog literature
    hit as direct sequence evidence, or a prediction as an observation)."""
    grounding = {g.claim_id: g for g in check_claim_grounding(state)}
    type_correctness = {t.evidence_id: t for t in check_evidence_type_correctness(state)}

    results = []
    for claim in state.claims:
        g = grounding[claim.claim_id]
        reasons = [] if g.grounded else [g.reason]
        for eid in claim.supporting_evidence_ids + claim.conflicting_evidence_ids:
            t = type_correctness.get(eid)
            if t is not None and not t.correct:
                reasons.append(f"cites evidence {eid!r} with an incorrect type/directness label: {t.reason}")
        reasons = [r for r in reasons if r]
        results.append(UnsupportedClaimResult(claim.claim_id, unsupported=bool(reasons), reason="; ".join(reasons)))
    return results


def classify_cross_source_consistency(state: InvestigationState) -> str:
    """Metric 5, per case: agreement / disagreement / incomparable / insufficient_evidence."""
    if not state.claims:
        return "insufficient_evidence"
    levels = {c.agreement for c in state.claims}
    if AgreementLevel.CONFLICT in levels:
        return "disagreement"
    if AgreementLevel.AGREE in levels:
        return "agreement"
    if AgreementLevel.PARTIAL in levels:
        return "incomparable"
    return "insufficient_evidence"


def check_end_to_end(case: BenchmarkCase, state: InvestigationState) -> tuple[str | None, str, bool | None]:
    """Metric 10 ingredients for one case. None/None when final_behavior is "not_evaluated"."""
    expected = None if case.expected.final_behavior == "not_evaluated" else case.expected.final_behavior
    actual = state.status.value
    match = None if expected is None else (expected == actual)
    return expected, actual, match


def evaluate_case(case: BenchmarkCase, state: InvestigationState) -> CaseEvaluation:
    expected, actual, match = check_end_to_end(case, state)
    return CaseEvaluation(
        case_id=case.case_id,
        identity_eval_class=classify_identity(case, state),
        source_checks=check_sources(case, state),
        provenance_checks=check_provenance(state),
        evidence_type_checks=check_evidence_type_correctness(state),
        claim_grounding_checks=check_claim_grounding(state),
        unsupported_claim_checks=check_unsupported_claims(state),
        cross_source_consistency=classify_cross_source_consistency(state),
        end_to_end_expected=expected,
        end_to_end_actual=actual,
        end_to_end_match=match,
    )
