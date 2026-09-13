"""Reliability scoring: turn a run's tool outcomes and verification findings into
a single, explainable report.

This is the concrete answer to "show how you know it works": rather than asserting
a run is trustworthy, curie computes a score from facts already logged during the
run (did the tools succeed, did independent sources agree) and lists the specific
caveats that lowered it.
"""

from __future__ import annotations

from curie.evaluation.models import ReliabilityReport
from curie.shared.models import AgreementLevel, ToolResult, ToolStatus, VerificationFinding


def score_run(
    tool_results: list[ToolResult], findings: list[VerificationFinding]
) -> ReliabilityReport:
    tools_called = len(tool_results)
    tools_failed = sum(
        1 for r in tool_results if r.status in (ToolStatus.ERROR, ToolStatus.TIMEOUT)
    )
    tools_not_implemented = sum(
        1 for r in tool_results if r.status == ToolStatus.NOT_IMPLEMENTED
    )
    tool_success_rate = (
        sum(1 for r in tool_results if r.status == ToolStatus.OK) / tools_called
        if tools_called
        else 0.0
    )

    counts = {level: 0 for level in AgreementLevel}
    for finding in findings:
        counts[finding.agreement] += 1

    scorable = counts[AgreementLevel.AGREE] + counts[AgreementLevel.CONFLICT]
    agreement_rate = (
        counts[AgreementLevel.AGREE] / scorable if scorable else 0.0
    )

    confidence_score = round(0.5 * tool_success_rate + 0.5 * agreement_rate, 3)

    caveats: list[str] = []
    if tools_failed:
        caveats.append(f"{tools_failed} of {tools_called} tool call(s) failed or timed out.")
    if tools_not_implemented:
        caveats.append(
            f"{tools_not_implemented} tool call(s) hit an interface stub, not a real integration."
        )
    if counts[AgreementLevel.CONFLICT]:
        caveats.append(
            f"{counts[AgreementLevel.CONFLICT]} verification finding(s) show sources in conflict."
        )
    if counts[AgreementLevel.UNVERIFIABLE]:
        caveats.append(
            f"{counts[AgreementLevel.UNVERIFIABLE]} finding(s) could not be verified from "
            "available evidence."
        )
    if not findings:
        caveats.append("No verification findings were computed for this run.")

    return ReliabilityReport(
        tool_success_rate=round(tool_success_rate, 3),
        tools_called=tools_called,
        tools_failed=tools_failed,
        tools_not_implemented=tools_not_implemented,
        agreement_rate=round(agreement_rate, 3),
        findings_agree=counts[AgreementLevel.AGREE],
        findings_conflict=counts[AgreementLevel.CONFLICT],
        findings_partial=counts[AgreementLevel.PARTIAL],
        findings_unverifiable=counts[AgreementLevel.UNVERIFIABLE],
        confidence_score=confidence_score,
        caveats=caveats,
    )
