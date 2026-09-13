"""Gemini reasoning/planning/synthesis tool.

Gemini is curie's reasoning layer, never its evidence layer: it drafts a
research plan and later narrates the deterministic evidence, but every
scientific claim still comes from a real tool call (UniProt/IEDB/Europe
PMC/ESM Atlas), and every deterministic decision — evidence_score, final
status, conflicts, provenance, source identifiers — stays untouched by it.
See `curie/agent/nodes/research_planner.py` and `gemini_synthesis.py` for
exactly where its output is consulted vs. where it is structurally unable to
matter.

Entirely optional end-to-end: if `GEMINI_API_KEY` is unset, or a call fails,
times out, or returns malformed structured output, callers fall back to
curie's existing fully-deterministic behavior. Gemini is never a single
point of failure and never gets a fabricated stand-in response — an
unavailable Gemini call is reported as `ToolStatus.SKIPPED` or `ERROR`, the
same honest reporting every other tool in this codebase uses.

Does not subclass `curie.tools.base.BaseToolClient`: that class builds an
`httpx.AsyncClient` per call, which doesn't fit the google-genai SDK's own
client/transport. `_run` below reproduces the same telemetry contract
(provider/operation/status/latency_ms/request_id/error, plus structured
logging) independently rather than forcing an httpx-shaped abstraction onto
a non-HTTP-shaped SDK.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError

from curie.shared.logging import get_logger
from curie.shared.models import ToolResult, ToolStatus

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class ResearchPlanSuggestion(BaseModel):
    """Structured planner output. Deliberately excludes `needs_identity`
    (trivially determined by whether an accession_hint was supplied — not a
    judgment call) and `structure_allowed` (a hard safety fact from sequence
    length, not a suggestion) — see research_planner.py for why those two
    stay 100% deterministic regardless of what Gemini proposes."""

    needs_epitope_evidence: bool
    needs_literature: bool
    needs_structure: bool
    reasoning: str = Field(description="1-2 plain-language sentences explaining this plan.")


class SynthesisResult(BaseModel):
    narrative: str = Field(
        description="A concise, plain-language narrative grounded strictly in the evidence provided."
    )


PLANNER_SYSTEM_INSTRUCTION = (
    "You are curie's research planner. You decide WHAT evidence to look for, "
    "never WHAT IS TRUE. You are given a normalized biological sequence's "
    "properties and a list of real tools available (UniProt, IEDB, Europe "
    "PMC, ESM Atlas) — you have not seen any results from them yet. Produce "
    "a structured plan for which of those tools are worth calling and a "
    "short reasoning for it. Do not claim to know this sequence's identity, "
    "structure, or epitopes. Do not invent database results."
)

SYNTHESIS_SYSTEM_INSTRUCTION = (
    "You are curie's evidence synthesizer. You are given ONLY the structured "
    "evidence curie's deterministic pipeline already retrieved and "
    "adjudicated — real tool results, evidence records, cross-source "
    "agreement findings, conflicts, and a final status/evidence_score that "
    "are already fixed and that you MUST NOT contradict or restate "
    "differently. Write a concise, plain-language narrative that helps a "
    "reader understand this evidence. Mandatory rules: "
    "(1) Do not invent evidence, identifiers, or citations beyond what is given. "
    "(2) Do not upgrade indirect evidence (e.g. homolog literature) into direct evidence. "
    "(3) Do not resolve conflicts by guessing which side is correct — describe the conflict instead. "
    "(4) If evidence is insufficient, say so plainly; do not paper over it. "
    "(5) Clearly distinguish what was retrieved from external sources from your own interpretation. "
    "(6) Never produce a clinical recommendation, therapeutic claim, or wet-lab protocol."
)


class GeminiClient:
    provider = "gemini"

    def __init__(self, api_key: str, model: str, timeout_seconds: float = 30.0) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._timeout_seconds = timeout_seconds

    async def _run(
        self, operation: str, schema: type[T], fn: Callable[[], Awaitable[types.GenerateContentResponse]]
    ) -> ToolResult:
        start = time.perf_counter()
        try:
            import asyncio

            response = await asyncio.wait_for(fn(), timeout=self._timeout_seconds)
            parsed = response.parsed
            if parsed is None or not isinstance(parsed, schema):
                raise ValueError(
                    f"Gemini did not return a valid {schema.__name__} "
                    f"(got {type(parsed).__name__ if parsed is not None else 'None'})"
                )
            latency_ms = (time.perf_counter() - start) * 1000
            result = ToolResult(
                provider=self.provider,
                operation=operation,
                status=ToolStatus.OK,
                latency_ms=latency_ms,
                data=parsed.model_dump(),
            )
        except TimeoutError:
            latency_ms = (time.perf_counter() - start) * 1000
            result = ToolResult(
                provider=self.provider,
                operation=operation,
                status=ToolStatus.TIMEOUT,
                latency_ms=latency_ms,
                error=f"Gemini call timed out after {self._timeout_seconds}s",
            )
        except (ValidationError, ValueError) as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            result = ToolResult(
                provider=self.provider,
                operation=operation,
                status=ToolStatus.ERROR,
                latency_ms=latency_ms,
                error=f"malformed structured output: {exc}",
            )
        except Exception as exc:  # noqa: BLE001 - reporting boundary, mirrors BaseToolClient.call
            latency_ms = (time.perf_counter() - start) * 1000
            result = ToolResult(
                provider=self.provider,
                operation=operation,
                status=ToolStatus.ERROR,
                latency_ms=latency_ms,
                error=str(exc),
            )

        logger.info(
            "tool_call",
            provider=result.provider,
            operation=result.operation,
            status=result.status.value,
            latency_ms=round(result.latency_ms, 1),
            request_id=result.request_id,
            error=result.error,
        )
        return result

    async def plan_research(
        self, sequence_type: str, sequence_length: int, accession_hint: str | None
    ) -> ToolResult:
        prompt = (
            f"Sequence type: {sequence_type}\n"
            f"Normalized length: {sequence_length} aa\n"
            f"Accession hint supplied: {'yes' if accession_hint else 'no'}\n"
            "Available tools: UniProt (identity/annotation), IEDB (curated "
            "epitope evidence, requires a resolved accession), Europe PMC "
            "(literature, requires a resolved protein name), ESM Atlas "
            "(structure prediction, works on any sequence up to ~400 aa).\n"
            "Investigation goal: assess what evidence can responsibly be "
            "gathered for this sequence and whether a confident conclusion "
            "is likely to be reachable."
        )

        async def _call() -> types.GenerateContentResponse:
            return await self._client.aio.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=PLANNER_SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=ResearchPlanSuggestion,
                    temperature=0.0,
                ),
            )

        return await self._run("planner", ResearchPlanSuggestion, _call)

    async def synthesize(self, evidence_summary: str) -> ToolResult:
        async def _call() -> types.GenerateContentResponse:
            return await self._client.aio.models.generate_content(
                model=self._model,
                contents=evidence_summary,
                config=types.GenerateContentConfig(
                    system_instruction=SYNTHESIS_SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=SynthesisResult,
                    temperature=0.2,
                ),
            )

        return await self._run("synthesis", SynthesisResult, _call)
