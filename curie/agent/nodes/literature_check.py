"""Literature check node.

Responsibility: ground the investigation in published literature via Europe PMC.
Runs after identity_resolution (it needs a protein name to search on) but is
independent of, and runs concurrently with, epitope_evidence.

A name-based literature search cannot guarantee an article is about this exact
sequence rather than a homolog, paralog, or a different strain sharing the same
annotated name — so every literature record here is marked INDIRECT by
construction, never DIRECT. That's a deliberate, conservative default, not an
oversight.
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
from curie.tools.europe_pmc import EuropePmcClient

logger = get_logger(__name__)

NODE_NAME = "literature_check"
MAX_RECORDS = 5


async def literature_check(state: InvestigationState) -> dict:
    start = time.perf_counter()

    if not state.protein_name:
        reason = "no protein_name established (requires resolved identity); " \
            "skipping literature search rather than querying on an arbitrary term"
        result = ToolResult(
            provider="europe_pmc",
            operation="search",
            status=ToolStatus.SKIPPED,
            latency_ms=0.0,
            error=reason,
        )
        evidence = EvidenceRecord(
            source="europe_pmc",
            source_type="literature",
            claim=f"Literature search skipped: {reason}.",
            evidence_type=EvidenceType.ABSENCE_OF_EVIDENCE,
            evidence_level=EvidenceLevel.NONE,
            directness=Directness.UNKNOWN,
        )
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info("literature_check", run_id=state.run_id, status="skipped")
        return {
            "tool_results": [result],
            "evidence": [evidence],
            "trace": [
                TraceEvent(
                    run_id=state.run_id,
                    node=NODE_NAME,
                    duration_ms=duration_ms,
                    status="skipped",
                    tools_called=["europe_pmc"],
                    output_summary=reason,
                    evidence_count=1,
                )
            ],
        }

    client = EuropePmcClient()
    query = f"{state.protein_name} epitope"
    result = await client.search(query, page_size=MAX_RECORDS)

    evidence_records: list[EvidenceRecord] = []
    malformed = result.ok and not isinstance(result.data, dict)

    if result.ok and malformed:
        evidence_records.append(
            EvidenceRecord(
                source="europe_pmc",
                source_type="literature",
                claim=f"Europe PMC returned an unexpected (non-object) response "
                f"shape for query '{query}'; treating as no usable result rather "
                f"than guessing at its structure.",
                evidence_type=EvidenceType.ABSENCE_OF_EVIDENCE,
                evidence_level=EvidenceLevel.NONE,
                directness=Directness.UNKNOWN,
                metadata={"query": query},
            )
        )
    elif result.ok:
        hit_count = result.data.get("hitCount", 0)
        articles = result.data.get("resultList", {}).get("result", [])
        if articles:
            for article in articles[:MAX_RECORDS]:
                pmid = article.get("id")
                evidence_records.append(
                    EvidenceRecord(
                        source="europe_pmc",
                        source_type="literature",
                        identifier=pmid,
                        claim=f"Literature record (matched by name, not by exact "
                        f"sequence): \"{article.get('title', 'untitled')}\"",
                        evidence_type=EvidenceType.LITERATURE,
                        evidence_level=EvidenceLevel.CURATED,
                        directness=Directness.INDIRECT,
                        source_url=f"https://europepmc.org/article/MED/{pmid}" if pmid else None,
                        metadata={
                            "title": article.get("title"),
                            "author_string": article.get("authorString"),
                            "pub_year": article.get("pubYear"),
                            "query": query,
                            "hit_count": hit_count,
                        },
                    )
                )
        else:
            evidence_records.append(
                EvidenceRecord(
                    source="europe_pmc",
                    source_type="literature",
                    claim=f"No literature found for '{query}'.",
                    evidence_type=EvidenceType.ABSENCE_OF_EVIDENCE,
                    evidence_level=EvidenceLevel.NONE,
                    directness=Directness.DIRECT,
                    metadata={"query": query},
                )
            )
    else:
        evidence_records.append(
            EvidenceRecord(
                source="europe_pmc",
                source_type="literature",
                claim=f"Europe PMC search failed: {result.error}",
                evidence_type=EvidenceType.ABSENCE_OF_EVIDENCE,
                evidence_level=EvidenceLevel.NONE,
                directness=Directness.UNKNOWN,
            )
        )

    duration_ms = (time.perf_counter() - start) * 1000
    trace_status = "error" if malformed else result.status.value
    logger.info("literature_check", run_id=state.run_id, status=trace_status, malformed=malformed)

    trace = TraceEvent(
        run_id=state.run_id,
        node=NODE_NAME,
        duration_ms=duration_ms,
        status=trace_status,
        tools_called=["europe_pmc"],
        input_summary=f"query={query!r}",
        output_summary=f"{len(evidence_records)} evidence record(s)",
        evidence_count=len(evidence_records),
        errors=(
            ["europe_pmc returned a malformed (non-object) response"]
            if malformed
            else ([] if result.ok else [result.error or "europe_pmc search failed"])
        ),
    )

    return {
        "tool_results": [result],
        "evidence": evidence_records,
        "trace": [trace],
    }
