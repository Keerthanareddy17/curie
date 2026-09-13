import httpx
import pytest

from curie.shared.models import ToolStatus
from curie.tools.base import BaseToolClient, ToolNotImplementedError


@pytest.fixture
def client():
    c = BaseToolClient(base_url="https://example.invalid")
    c.provider = "test_provider"
    return c


async def test_call_success_sets_ok_and_data(client):
    async def fn(_http_client):
        return {"hello": "world"}

    result = await client.call("do_thing", fn)

    assert result.status == ToolStatus.OK
    assert result.provider == "test_provider"
    assert result.operation == "do_thing"
    assert result.data == {"hello": "world"}
    assert result.latency_ms >= 0
    assert result.request_id
    assert result.error is None
    assert result.ok is True


async def test_call_not_implemented(client):
    async def fn(_http_client):
        raise ToolNotImplementedError("not built yet")

    result = await client.call("do_thing", fn)

    assert result.status == ToolStatus.NOT_IMPLEMENTED
    assert result.error == "not built yet"
    assert result.ok is False


async def test_call_generic_error(client):
    async def fn(_http_client):
        raise ValueError("boom")

    result = await client.call("do_thing", fn)

    assert result.status == ToolStatus.ERROR
    assert "boom" in result.error


async def test_call_timeout(client):
    async def fn(_http_client):
        raise httpx.TimeoutException("timed out")

    result = await client.call("do_thing", fn)

    assert result.status == ToolStatus.TIMEOUT


async def test_every_result_has_a_unique_request_id(client):
    async def fn(_http_client):
        return None

    r1 = await client.call("op", fn)
    r2 = await client.call("op", fn)
    assert r1.request_id != r2.request_id
