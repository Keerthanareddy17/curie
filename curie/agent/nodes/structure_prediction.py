"""Structure prediction node.

Responsibility: obtain a real structure prediction from ESM Atlas for the
normalized sequence. Runs independently of identity resolution — folding doesn't
need to know what the protein is called, only its residues — so this node has no
data dependency on identity_resolution and the graph runs them concurrently
(see agent/graph.py).

Sequences over MAX_SEQUENCE_LENGTH are never sent to ESM Atlas at all: this node
checks length itself and records a structured SKIPPED result, rather than
truncating the sequence and folding a partial structure that could be mistaken
for the whole protein's.
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
    ToolResult,
    ToolStatus,
    TraceEvent,
)
from curie.tools.esm_atlas import MAX_SEQUENCE_LENGTH, EsmAtlasClient, mean_plddt

logger = get_logger(__name__)

NODE_NAME = "structure_prediction"


async def structure_prediction(state: InvestigationState) -> dict:
    start = time.perf_counter()
    sequence = state.normalized_sequence

    if not sequence or len(sequence) > MAX_SEQUENCE_LENGTH:
        reason = (
            "no normalized sequence available"
            if not sequence
            else f"sequence length {len(sequence)} exceeds supported fold length ({MAX_SEQUENCE_LENGTH} aa)"
        )
        result = ToolResult(
            provider="esm_atlas",
            operation="fold_sequence",
            status=ToolStatus.SKIPPED,
            latency_ms=0.0,
            error=reason,
        )
        evidence = EvidenceRecord(
            source="esm_atlas",
            source_type="prediction",
            claim=f"Structure prediction skipped: {reason}.",
            evidence_type=EvidenceType.ABSENCE_OF_EVIDENCE,
            evidence_level=EvidenceLevel.NONE,
            directness=Directness.DIRECT,
        )
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info("structure_prediction", run_id=state.run_id, status="skipped", reason=reason)
        return {
            "tool_results": [result],
            "evidence": [evidence],
            "trace": [
                TraceEvent(
                    run_id=state.run_id,
                    node=NODE_NAME,
                    duration_ms=duration_ms,
                    status="skipped",
                    tools_called=["esm_atlas"],
                    input_summary=f"normalized_length={len(sequence)}",
                    output_summary=reason,
                    evidence_count=1,
                )
            ],
        }

    client = EsmAtlasClient()
    result = await client.fold_sequence(sequence)

    if result.ok:
        confidence = mean_plddt(result.data)
        claim = f"ESM Atlas predicted a structure for all {len(sequence)} residues"
        if confidence is not None:
            claim += f" (mean predicted confidence {confidence:.1f}/100)"
        evidence = EvidenceRecord(
            source="esm_atlas",
            source_type="prediction",
            claim=claim + ".",
            evidence_type=EvidenceType.PREDICTED_STRUCTURE,
            evidence_level=EvidenceLevel.PREDICTED,
            directness=Directness.DIRECT,
            confidence=confidence,
            metadata={"pdb_length_bytes": len(result.data)},
        )
    else:
        evidence = EvidenceRecord(
            source="esm_atlas",
            source_type="prediction",
            claim=f"ESM Atlas fold failed: {result.error}",
            evidence_type=EvidenceType.ABSENCE_OF_EVIDENCE,
            evidence_level=EvidenceLevel.NONE,
            directness=Directness.DIRECT,
        )

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info("structure_prediction", run_id=state.run_id, status=result.status.value)

    trace = TraceEvent(
        run_id=state.run_id,
        node=NODE_NAME,
        duration_ms=duration_ms,
        status=result.status.value,
        tools_called=["esm_atlas"],
        input_summary=f"normalized_length={len(sequence)}",
        output_summary=evidence.claim,
        evidence_count=1,
        errors=[] if result.ok else [result.error or "esm_atlas fold failed"],
    )

    return {
        "tool_results": [result],
        "evidence": [evidence],
        "trace": [trace],
    }
