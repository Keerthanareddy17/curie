"""Shared typed models used across tools/, agent/, and evaluation/.

Kept in one place so a `ToolResult` means the same thing everywhere it appears,
rather than each tool inventing its own response shape.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid4().hex[:12]


class ToolStatus(str, Enum):
    OK = "ok"
    ERROR = "error"
    NOT_IMPLEMENTED = "not_implemented"
    TIMEOUT = "timeout"
    # A node deliberately chose not to make this call (sequence too long for
    # ESM Atlas, or no resolved identity to query IEDB/Europe PMC with) — a
    # policy decision the graph made, distinct from NOT_IMPLEMENTED (the
    # integration doesn't exist in code) or ERROR (we tried and it failed).
    SKIPPED = "skipped"


class ToolResult(BaseModel):
    """The mandatory envelope every external tool call returns.

    provider/operation/status/latency_ms/request_id/error are non-negotiable per
    the project spec: every external call must eventually expose all six, so a
    dossier can always answer "where did this come from, did it succeed, how
    long did it take, and can I trace it back to a specific call."
    """

    provider: str
    operation: str
    status: ToolStatus
    latency_ms: float
    request_id: str = Field(default_factory=_new_id)
    error: str | None = None
    data: Any = None
    fetched_at: datetime = Field(default_factory=_now)

    @property
    def ok(self) -> bool:
        return self.status == ToolStatus.OK


class AgreementLevel(str, Enum):
    AGREE = "agree"
    PARTIAL = "partial"
    CONFLICT = "conflict"
    UNVERIFIABLE = "unverifiable"


class VerificationFinding(BaseModel):
    """One cross-source consistency check performed by evidence adjudication."""

    claim: str
    supporting_sources: list[str] = Field(default_factory=list)
    conflicting_sources: list[str] = Field(default_factory=list)
    agreement: AgreementLevel
    notes: str = ""


# --- Investigation domain model ------------------------------------------------


class SequenceType(str, Enum):
    PROTEIN = "protein"
    NUCLEOTIDE = "nucleotide"
    UNKNOWN = "unknown"


class IdentityStatus(str, Enum):
    # Identity taken from a caller-supplied accession, confirmed by a successful
    # UniProt lookup on it. Not an independent discovery.
    RESOLVED_HINT = "resolved_hint"
    # No accession was supplied, or the supplied one didn't resolve. curie does
    # not perform sequence-homology search, so this is the honest default — see
    # docs/LIMITATIONS.md. Never silently upgraded to a resolved identity.
    UNRESOLVED = "unresolved"


class InvestigationStatus(str, Enum):
    PLANNING = "planning"
    COLLECTING = "collecting"
    ADJUDICATING = "adjudicating"
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    CONFLICTING = "conflicting"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    FAILED = "failed"


class EvidenceType(str, Enum):
    SEQUENCE_IDENTITY = "sequence_identity"
    CURATED_ANNOTATION = "curated_annotation"
    EXPERIMENTAL_STRUCTURE = "experimental_structure"
    PREDICTED_STRUCTURE = "predicted_structure"
    CURATED_EPITOPE = "curated_epitope"
    PREDICTED_EPITOPE = "predicted_epitope"
    LITERATURE = "literature"
    ABSENCE_OF_EVIDENCE = "absence_of_evidence"


class EvidenceLevel(str, Enum):
    CURATED = "curated"
    OBSERVED = "observed"
    PREDICTED = "predicted"
    NONE = "none"


class Directness(str, Enum):
    DIRECT = "direct"
    INDIRECT = "indirect"
    UNKNOWN = "unknown"


class EvidenceRecord(BaseModel):
    """One normalized fact contributed by a tool call, independent of which
    provider produced it. Every node that calls a real API turns its response
    into zero or more of these instead of handing raw payloads downstream."""

    evidence_id: str = Field(default_factory=_new_id)
    source: str
    source_type: str
    identifier: str | None = None
    claim: str
    evidence_type: EvidenceType
    evidence_level: EvidenceLevel
    directness: Directness
    confidence: float | None = None
    source_url: str | None = None
    retrieved_at: datetime = Field(default_factory=_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CandidateProtein(BaseModel):
    accession: str
    name: str | None = None
    organism: str | None = None
    match_type: str  # currently only "accession_hint" — see IdentityStatus
    source: str = "uniprot"


class Claim(BaseModel):
    """One thing the adjudicator checked across evidence records, and what it found."""

    claim_id: str = Field(default_factory=_new_id)
    statement: str
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    conflicting_evidence_ids: list[str] = Field(default_factory=list)
    agreement: AgreementLevel
    notes: str = ""


class EvidenceConflict(BaseModel):
    conflict_id: str = Field(default_factory=_new_id)
    claim: str
    evidence_a: str
    evidence_b: str
    conflict_type: str
    severity: str  # "low" | "medium" | "high"
    resolved: bool = False
    notes: str = ""


class ResearchPlan(BaseModel):
    """What the planner decided to look for. Never a claim about what is true —
    see curie/agent/nodes/research_planner.py."""

    needs_identity: bool
    needs_epitope_evidence: bool
    needs_literature: bool
    needs_structure: bool
    structure_allowed: bool
    reasoning: str


class TraceEvent(BaseModel):
    run_id: str
    node: str
    timestamp: datetime = Field(default_factory=_now)
    duration_ms: float
    status: str
    tools_called: list[str] = Field(default_factory=list)
    input_summary: str = ""
    output_summary: str = ""
    evidence_count: int = 0
    evidence_score: float | None = None
    errors: list[str] = Field(default_factory=list)


class Dossier(BaseModel):
    """The final structured report. Assembled deterministically from state —
    see curie/agent/nodes/dossier_generation.py. Not clinical, not a therapeutic
    recommendation, not wet-lab guidance: see docs/LIMITATIONS.md."""

    investigation_id: str
    generated_at: datetime = Field(default_factory=_now)
    sequence_summary: str
    sequence_type: SequenceType
    identity_result: str
    identity_evidence: list[str] = Field(default_factory=list)
    structural_evidence: list[str] = Field(default_factory=list)
    epitope_evidence: list[str] = Field(default_factory=list)
    literature_evidence: list[str] = Field(default_factory=list)
    cross_source_agreement: str
    conflicts: list[EvidenceConflict] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    evidence_score: float
    final_status: InvestigationStatus
    provenance: list[ToolResult] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    next_research_questions: list[str] = Field(default_factory=list)
    ai_synthesis: str | None = Field(
        default=None,
        description="Optional Gemini-narrated summary of the evidence above. "
        "Purely descriptive: it cannot change evidence_score, final_status, "
        "conflicts, or provenance, all of which are fixed before this is "
        "generated. None when GEMINI_API_KEY is unset or the call failed — "
        "see curie/agent/nodes/gemini_synthesis.py.",
    )
