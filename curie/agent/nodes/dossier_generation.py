"""Dossier generation node.

Responsibility: assemble the final structured report entirely from state — no LLM
call. Given no API key is wired up for this phase and every field required
(sequence summary, identity, evidence groupings, conflicts, missing evidence,
score, status) is already structured data on `InvestigationState`, templating it
directly keeps the dossier 100% reproducible and independently testable. An LLM
summarization pass is a reasonable future addition (explicitly allowed by the
spec to *summarize*, never to override structured determinations) but isn't
needed to produce a real, evidence-grounded report today.
"""

from __future__ import annotations

import time

from curie.agent.state import InvestigationState
from curie.shared.logging import get_logger
from curie.shared.models import Dossier, EvidenceType, IdentityStatus, TraceEvent

logger = get_logger(__name__)

NODE_NAME = "dossier_generation"

LIMITATIONS = [
    "curie is research and education software: it does not produce clinically "
    "validated results, does not recommend a therapeutic or vaccine candidate, "
    "and is not wet-lab ready.",
    "curie does not perform sequence-homology search; identity is only resolved "
    "when an accession is supplied and confirmed against UniProt.",
    "Any score or status here is a computed summary of what curie's tools "
    "returned at run time, not a claim of biological truth.",
]


def _identity_result_text(state: InvestigationState) -> str:
    if state.identity_status == IdentityStatus.RESOLVED_HINT and state.candidate_proteins:
        candidate = state.candidate_proteins[0]
        return (
            f"Resolved via supplied accession hint: {candidate.accession} "
            f"({candidate.name or 'name unavailable'}"
            + (f", {candidate.organism}" if candidate.organism else "")
            + ")."
        )
    return "UNRESOLVED — no accession hint was supplied, or it did not resolve. " \
        "curie does not perform sequence-homology search (see docs/LIMITATIONS.md)."


def _evidence_ids_by_type(state: InvestigationState, evidence_type: EvidenceType) -> list[str]:
    return [r.evidence_id for r in state.evidence if r.evidence_type == evidence_type]


def _cross_source_agreement_text(state: InvestigationState) -> str:
    if not state.claims:
        return "No cross-source checks were computed."
    agree = sum(1 for c in state.claims if c.agreement.value == "agree")
    conflict = sum(1 for c in state.claims if c.agreement.value == "conflict")
    unverifiable = sum(1 for c in state.claims if c.agreement.value == "unverifiable")
    partial = sum(1 for c in state.claims if c.agreement.value == "partial")
    return (
        f"{agree} of {len(state.claims)} check(s) agree, {conflict} conflict, "
        f"{partial} partial, {unverifiable} unverifiable."
    )


def _next_research_questions(state: InvestigationState) -> list[str]:
    questions: list[str] = []
    if state.identity_status == IdentityStatus.UNRESOLVED:
        questions.append(
            "Confirm sequence identity via a proper sequence-similarity search "
            "(e.g. BLAST against UniProt/NCBI) rather than an accession hint."
        )
    if state.identity_status == IdentityStatus.UNRESOLVED and any(
        r.evidence_type == EvidenceType.PREDICTED_STRUCTURE for r in state.evidence
    ):
        questions.append(
            "Repeat epitope and literature queries once identity is confirmed — "
            "they were skipped or limited without it."
        )
    structure_records = [r for r in state.evidence if r.evidence_type == EvidenceType.PREDICTED_STRUCTURE]
    if structure_records and (structure_records[0].confidence or 100) < 70:
        questions.append(
            "Predicted structure confidence is low; treat structural conclusions "
            "cautiously pending a higher-confidence or experimental structure."
        )
    if any(r.evidence_type == EvidenceType.ABSENCE_OF_EVIDENCE and r.source == "iedb" for r in state.evidence):
        questions.append(
            "No curated IEDB epitopes were found for this target; absence of "
            "curated evidence is not evidence of biological absence."
        )
    if not questions:
        questions.append("No specific follow-up gaps were identified from this run's evidence.")
    return questions


def dossier_generation(state: InvestigationState) -> dict:
    start = time.perf_counter()

    dossier = Dossier(
        investigation_id=state.run_id,
        sequence_summary=f"{len(state.normalized_sequence)}-residue {state.sequence_type.value} sequence"
        + (f" (translated from {state.sequence_type.value} input)" if state.translated_sequence else ""),
        sequence_type=state.sequence_type,
        identity_result=_identity_result_text(state),
        identity_evidence=_evidence_ids_by_type(state, EvidenceType.CURATED_ANNOTATION)
        + _evidence_ids_by_type(state, EvidenceType.SEQUENCE_IDENTITY),
        structural_evidence=_evidence_ids_by_type(state, EvidenceType.PREDICTED_STRUCTURE)
        + _evidence_ids_by_type(state, EvidenceType.EXPERIMENTAL_STRUCTURE),
        epitope_evidence=_evidence_ids_by_type(state, EvidenceType.CURATED_EPITOPE)
        + _evidence_ids_by_type(state, EvidenceType.PREDICTED_EPITOPE),
        literature_evidence=_evidence_ids_by_type(state, EvidenceType.LITERATURE),
        cross_source_agreement=_cross_source_agreement_text(state),
        conflicts=state.conflicts,
        missing_evidence=state.missing_evidence,
        evidence_score=state.evidence_score or 0.0,
        final_status=state.status,
        provenance=state.tool_results,
        limitations=LIMITATIONS,
        next_research_questions=_next_research_questions(state),
        ai_synthesis=state.ai_synthesis,
    )

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info("dossier_generation", run_id=state.run_id, final_status=state.status.value)

    trace = TraceEvent(
        run_id=state.run_id,
        node=NODE_NAME,
        duration_ms=duration_ms,
        status="ok",
        output_summary=f"dossier generated, final_status={state.status.value}",
        evidence_score=state.evidence_score,
    )

    return {"dossier": dossier, "trace": [trace]}
