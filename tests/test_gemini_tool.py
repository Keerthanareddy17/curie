"""Unit tests for curie/tools/gemini.py's GeminiClient — mocked at the SDK
boundary (no real API calls, no API key required). Covers the explicit
regression list: planner success, malformed output, unavailable/timeout,
synthesis failure.
"""

from __future__ import annotations

import asyncio

import pytest

from curie.shared.models import ToolStatus
from curie.tools.gemini import GeminiClient, ResearchPlanSuggestion, SynthesisResult


class _FakeResponse:
    def __init__(self, parsed):
        self.parsed = parsed


class _FakeModels:
    def __init__(self, fake_generate_content):
        self.generate_content = fake_generate_content


class _FakeAio:
    def __init__(self, fake_generate_content):
        self.models = _FakeModels(fake_generate_content)


class _FakeGenaiClient:
    """Replaces GeminiClient._client wholesale — google.genai.Client's `.aio`
    is a read-only property, so it can't be patched on a real instance."""

    def __init__(self, fake_generate_content):
        self.aio = _FakeAio(fake_generate_content)


def _client_with_fake_generate_content(fake_generate_content):
    client = GeminiClient(api_key="fake-key-not-used", model="fake-model")
    client._client = _FakeGenaiClient(fake_generate_content)
    return client


async def test_plan_research_success_returns_ok_with_structured_data():
    suggestion = ResearchPlanSuggestion(
        needs_epitope_evidence=True, needs_literature=False, needs_structure=True, reasoning="short peptide"
    )

    async def fake_generate_content(**kwargs):
        return _FakeResponse(parsed=suggestion)

    client = _client_with_fake_generate_content(fake_generate_content)
    result = await client.plan_research(sequence_type="protein", sequence_length=50, accession_hint=None)

    assert result.status == ToolStatus.OK
    assert result.provider == "gemini"
    assert result.operation == "planner"
    assert result.data["needs_literature"] is False
    assert result.request_id
    assert result.latency_ms >= 0


async def test_plan_research_malformed_output_is_reported_as_error_not_crash():
    async def fake_generate_content(**kwargs):
        return _FakeResponse(parsed=None)  # SDK failed to produce valid structured output

    client = _client_with_fake_generate_content(fake_generate_content)
    result = await client.plan_research(sequence_type="protein", sequence_length=50, accession_hint=None)

    assert result.status == ToolStatus.ERROR
    assert "malformed" in result.error.lower()


async def test_plan_research_wrong_schema_type_is_malformed():
    async def fake_generate_content(**kwargs):
        return _FakeResponse(parsed=SynthesisResult(narrative="wrong schema entirely"))

    client = _client_with_fake_generate_content(fake_generate_content)
    result = await client.plan_research(sequence_type="protein", sequence_length=50, accession_hint=None)

    assert result.status == ToolStatus.ERROR


async def test_plan_research_timeout_is_reported_as_timeout_not_crash():
    async def fake_generate_content(**kwargs):
        await asyncio.sleep(10)

    client = GeminiClient(api_key="fake-key", model="fake-model", timeout_seconds=0.05)
    client._client = _FakeGenaiClient(fake_generate_content)
    result = await client.plan_research(sequence_type="protein", sequence_length=50, accession_hint=None)

    assert result.status == ToolStatus.TIMEOUT


async def test_plan_research_generic_exception_is_reported_as_error():
    async def fake_generate_content(**kwargs):
        raise RuntimeError("service unavailable")

    client = _client_with_fake_generate_content(fake_generate_content)
    result = await client.plan_research(sequence_type="protein", sequence_length=50, accession_hint=None)

    assert result.status == ToolStatus.ERROR
    assert "service unavailable" in result.error


async def test_synthesize_success_returns_narrative():
    async def fake_generate_content(**kwargs):
        return _FakeResponse(parsed=SynthesisResult(narrative="Evidence agrees across sources."))

    client = _client_with_fake_generate_content(fake_generate_content)
    result = await client.synthesize("some evidence summary")

    assert result.status == ToolStatus.OK
    assert result.operation == "synthesis"
    assert result.data["narrative"] == "Evidence agrees across sources."


async def test_synthesize_failure_is_reported_not_faked():
    async def fake_generate_content(**kwargs):
        raise RuntimeError("500 internal error")

    client = _client_with_fake_generate_content(fake_generate_content)
    result = await client.synthesize("some evidence summary")

    assert result.status == ToolStatus.ERROR
    assert result.data is None  # no fabricated narrative on failure
