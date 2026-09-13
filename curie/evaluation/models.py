"""Typed models for the evaluation layer.

Separate from curie/shared/models.py because these describe *judgments about a run*,
not the run's own evidence — evaluation is a consumer of agent output, not a
participant in producing it.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from curie.shared.models import InvestigationStatus, ToolStatus, VerificationFinding


class ReliabilityReport(BaseModel):
    """A deterministic, explainable summary of how trustworthy one run's evidence is.

    Every field here is computed from data already on the run's state (tool call
    outcomes, verification findings) — nothing here is a model-generated opinion.
    """

    tool_success_rate: float
    tools_called: int
    tools_failed: int
    tools_not_implemented: int
    agreement_rate: float
    findings_agree: int
    findings_conflict: int
    findings_partial: int
    findings_unverifiable: int
    confidence_score: float = Field(
        description="0-1 composite of tool_success_rate and agreement_rate. "
        "Not a probability of scientific correctness — see docs/LIMITATIONS.md."
    )
    caveats: list[str] = Field(default_factory=list)


class EvaluationCase(BaseModel):
    """One fixture-driven test case for the evaluation harness."""

    case_id: str
    sequence: str
    accession_hint: str | None = None
    description: str = ""
    expect_min_evidence_score: float | None = None
    expect_status: InvestigationStatus | None = None


class EvaluationCaseResult(BaseModel):
    case_id: str
    run_id: str
    evidence_score: float
    status: InvestigationStatus
    passed: bool | None = None
    notes: str = ""


# --- Phase 3 benchmark schema ---------------------------------------------
#
# Distinct from EvaluationCase/EvaluationCaseResult above (Phase 2's simple
# harness, kept working and unchanged). A BenchmarkCase carries an *expected*
# outcome sourced from public biology (UniProt/IEDB/literature), never from the
# system's own prior output, so a benchmark run can be scored against it.


class IdentityEvalClass(str, Enum):
    """How a case's identity ground truth may legitimately be used in scoring.

    This exists specifically to enforce the "no free information" rule: a case
    that supplies `accession_hint` must never have its identity outcome counted
    as evidence of independent resolution ability, because the evaluator handed
    the answer to the system as an input.
    """

    SUPPLIED = "identity_supplied"
    """accession_hint was given. Excluded from any identity-accuracy metric."""
    RESOLVED = "identity_resolved"
    """No hint was given and the system nonetheless independently resolved
    identity. Not reachable by the current implementation (see
    docs/LIMITATIONS.md) — kept in the enum so the report can say so honestly
    rather than omitting the case entirely."""
    UNRESOLVED = "identity_unresolved"
    """No hint was given and the system correctly stayed UNRESOLVED rather
    than guessing — the expected, correct behavior today."""
    NOT_EVALUATED = "identity_not_evaluated"
    """This case's expected.identity.status is "not_evaluated" — identity
    was never claimed as a gold label for it."""


class ExpectedIdentity(BaseModel):
    status: str = "not_evaluated"  # "not_evaluated" | "resolved" | "unresolved"
    accession: str | None = None


class EvidenceExpectation(BaseModel):
    source: str  # "uniprot" | "iedb" | "europe_pmc" | "esm_atlas"
    should_be_called: bool = True
    expect_status: str | None = None  # ToolStatus value, or None = not_evaluated
    expect_evidence_type: str | None = None  # EvidenceType value, or None
    notes: str = ""


class ExpectedOutcome(BaseModel):
    identity: ExpectedIdentity = Field(default_factory=ExpectedIdentity)
    sources: list[str] = Field(default_factory=list)
    evidence_expectations: list[EvidenceExpectation] = Field(default_factory=list)
    final_behavior: str = "not_evaluated"  # InvestigationStatus value, or "not_evaluated"


class BenchmarkCase(BaseModel):
    """One real, publicly-verifiable protein test case.

    `accession_hint` here is deliberately part of the INPUT, mirroring the
    real API — never smuggled in as part of `expected`. See
    curie/evaluation/datasets/README.md for how each case's `expected` block
    was sourced.
    """

    case_id: str
    description: str
    sequence: str
    sequence_type: str = "protein"
    accession_hint: str | None = None
    expected: ExpectedOutcome = Field(default_factory=ExpectedOutcome)


# --- Fault-injection scenario results ---------------------------------------


class ScenarioCheck(BaseModel):
    """One specific, named assertion within a fault-injection scenario."""

    description: str
    passed: bool
    detail: str = ""


class ScenarioResult(BaseModel):
    scenario_id: str
    title: str
    injected_fault: str
    expected_behavior: str
    actual_behavior: str
    passed: bool
    crashed: bool = False
    checks: list[ScenarioCheck] = Field(default_factory=list)
    run_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    """Which cross-cutting metrics (report.py) this scenario feeds:
    "tool_recovery", "abstention_expected", "conflict_expected", or
    "conflict_not_expected". A scenario can carry several."""
    conflict_detected: bool = False
    final_status: str | None = None
    identity_status: str | None = None


__all__ = [
    "ReliabilityReport",
    "EvaluationCase",
    "EvaluationCaseResult",
    "ToolStatus",
    "VerificationFinding",
    "IdentityEvalClass",
    "ExpectedIdentity",
    "EvidenceExpectation",
    "ExpectedOutcome",
    "BenchmarkCase",
    "ScenarioCheck",
    "ScenarioResult",
]
