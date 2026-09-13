"""Epitope evidence node.

Responsibility: gather curated epitope evidence from IEDB for the resolved
protein. Runs after identity_resolution (it needs an accession) but is
independent of, and runs concurrently with, literature_check (see agent/graph.py).

IEDB's curated records are the real thing this project cares about — not a
predictor. Every record returned is tagged CURATED, never described as
"predicted" or "experimentally validated" beyond what IEDB itself asserts. An
empty result set is reported as "no direct curated evidence found" (a real,
informative finding) rather than treated as an error or silently dropped.
"""

from __future__ import annotations

import time

from curie.agent.state import InvestigationState
from curie.shared.logging import get_logger
from curie.shared.models import (
    Directness,
    EvidenceLevel,
    EvidenceRecord,
    EvidenceType,
    IdentityStatus,
    ToolResult,
    ToolStatus,
    TraceEvent,
)
from curie.tools.iedb import IedbClient

logger = get_logger(__name__)

NODE_NAME = "epitope_evidence"


async def epitope_evidence(state: InvestigationState) -> dict:
    start = time.perf_counter()
    accession = state.candidate_proteins[0].accession if state.candidate_proteins else None

    if state.identity_status != IdentityStatus.RESOLVED_HINT or not accession:
        reason = "identity unresolved; cannot query IEDB by source accession"
        result = ToolResult(
            provider="iedb",
            operation="search_epitopes_by_source_accession",
            status=ToolStatus.SKIPPED,
            latency_ms=0.0,
            error=reason,
        )
        evidence = EvidenceRecord(
            source="iedb",
            source_type="database",
            claim=f"Epitope evidence query skipped: {reason}.",
            evidence_type=EvidenceType.ABSENCE_OF_EVIDENCE,
            evidence_level=EvidenceLevel.NONE,
            directness=Directness.UNKNOWN,
        )
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info("epitope_evidence", run_id=state.run_id, status="skipped")
        return {
            "tool_results": [result],
            "evidence": [evidence],
            "trace": [
                TraceEvent(
                    run_id=state.run_id,
                    node=NODE_NAME,
                    duration_ms=duration_ms,
                    status="skipped",
                    tools_called=["iedb"],
                    output_summary=reason,
                    evidence_count=1,
                )
            ],
        }

    client = IedbClient()
    result = await client.search_epitopes_by_source_accession(accession)

    if result.ok:
        records = result.data if isinstance(result.data, list) else []
        if records:
            sequences = [r.get("linear_sequence") for r in records[:10] if r.get("linear_sequence")]
            evidence = EvidenceRecord(
                source="iedb",
                source_type="database",
                identifier=accession,
                claim=f"IEDB has {len(records)} curated epitope record(s) for {accession}.",
                evidence_type=EvidenceType.CURATED_EPITOPE,
                evidence_level=EvidenceLevel.CURATED,
                directness=Directness.DIRECT,
                source_url=f"https://www.iedb.org/",
                metadata={"epitope_count": len(records), "example_sequences": sequences},
            )
        else:
            evidence = EvidenceRecord(
                source="iedb",
                source_type="database",
                identifier=accession,
                claim=f"No direct curated evidence found in IEDB for {accession}.",
                evidence_type=EvidenceType.ABSENCE_OF_EVIDENCE,
                evidence_level=EvidenceLevel.NONE,
                directness=Directness.DIRECT,
            )
    else:
        evidence = EvidenceRecord(
            source="iedb",
            source_type="database",
            identifier=accession,
            claim=f"IEDB lookup for {accession} failed: {result.error}",
            evidence_type=EvidenceType.ABSENCE_OF_EVIDENCE,
            evidence_level=EvidenceLevel.NONE,
            directness=Directness.DIRECT,
        )

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info("epitope_evidence", run_id=state.run_id, status=result.status.value)

    trace = TraceEvent(
        run_id=state.run_id,
        node=NODE_NAME,
        duration_ms=duration_ms,
        status=result.status.value,
        tools_called=["iedb"],
        input_summary=f"accession={accession}",
        output_summary=evidence.claim,
        evidence_count=1,
        errors=[] if result.ok else [result.error or "iedb lookup failed"],
    )

    return {
        "tool_results": [result],
        "evidence": [evidence],
        "trace": [trace],
    }
