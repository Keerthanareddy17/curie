"""Typed LangGraph state for curie's investigation graph.

`tool_results`, `evidence`, `trace`, and `errors` use an `operator.add` reducer
because multiple nodes write them *in the same superstep* — structure_prediction
runs concurrently with identity_resolution, and epitope_evidence runs concurrently
with literature_check (see agent/graph.py). Without a reducer, two concurrent
writers to the same plain field would conflict; each node here returns only its
own new items and the reducer concatenates them. Every other field has exactly
one writer node and uses ordinary replace semantics.
"""

from __future__ import annotations

import operator
from typing import Annotated
from uuid import uuid4

from pydantic import BaseModel, Field

from curie.shared.models import (
    CandidateProtein,
    Claim,
    Dossier,
    EvidenceConflict,
    EvidenceRecord,
    IdentityStatus,
    InvestigationStatus,
    ResearchPlan,
    SequenceType,
    ToolResult,
    TraceEvent,
)


def _new_run_id() -> str:
    return "inv-" + uuid4().hex[:12]


class InvestigationState(BaseModel):
    # --- input ---
    run_id: str = Field(default_factory=_new_run_id)
    raw_sequence: str
    accession_hint: str | None = Field(
        default=None,
        description="Optional known UniProt accession for the input sequence. "
        "curie does not do sequence-homology search to discover this on its own "
        "(see docs/LIMITATIONS.md); without it, identity_status stays UNRESOLVED.",
    )
    notes: str = ""

    # --- sequence_intake output ---
    normalized_sequence: str = ""
    translated_sequence: str | None = None
    sequence_type: SequenceType = SequenceType.UNKNOWN
    residue_composition: dict[str, float] = Field(default_factory=dict)
    mean_hydrophobicity: float | None = None
    mean_antigenicity: float | None = None

    # --- research_planner output ---
    research_plan: ResearchPlan | None = None

    # --- identity_resolution output ---
    identity_status: IdentityStatus = IdentityStatus.UNRESOLVED
    candidate_proteins: list[CandidateProtein] = Field(default_factory=list)
    protein_name: str | None = None

    # --- accumulated across all tool-calling nodes (concurrent writers) ---
    tool_results: Annotated[list[ToolResult], operator.add] = Field(default_factory=list)
    evidence: Annotated[list[EvidenceRecord], operator.add] = Field(default_factory=list)
    trace: Annotated[list[TraceEvent], operator.add] = Field(default_factory=list)
    errors: Annotated[list[str], operator.add] = Field(default_factory=list)

    # --- evidence_adjudication output ---
    claims: list[Claim] = Field(default_factory=list)
    conflicts: list[EvidenceConflict] = Field(default_factory=list)
    evidence_score: float | None = None
    missing_evidence: list[str] = Field(default_factory=list)

    # --- confidence_gate output ---
    status: InvestigationStatus = InvestigationStatus.PLANNING

    # --- gemini_synthesis output ---
    ai_synthesis: str | None = None

    # --- dossier_generation output ---
    dossier: Dossier | None = None
