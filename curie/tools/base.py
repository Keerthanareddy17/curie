"""Base class for external tool clients.

Every real tool client (esm_atlas.py, uniprot.py, iedb.py, europe_pmc.py) subclasses
`BaseToolClient` and implements one thing: how to make its specific HTTP call. The base
class owns timing, status classification, structured logging, and building the
`ToolResult` envelope, so no subclass can "forget" to report latency or an error and
no subclass can fabricate a success it didn't earn.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from curie.shared.logging import get_logger
from curie.shared.models import ToolResult, ToolStatus

logger = get_logger(__name__)


class ToolNotImplementedError(NotImplementedError):
    """Raised by a tool operation that is an interface stub, not a real call.

    Caught by `BaseToolClient.call` and turned into a `ToolStatus.NOT_IMPLEMENTED`
    result rather than an exception escaping to the caller — a stub is a known,
    reportable state, not a crash.
    """


class BaseToolClient:
    provider: str = "unknown"

    def __init__(self, base_url: str, timeout_seconds: float = 20.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def call(
        self,
        operation: str,
        fn: Callable[[httpx.AsyncClient], Awaitable[Any]],
    ) -> ToolResult:
        """Run `fn` against a fresh AsyncClient and wrap the outcome as a ToolResult.

        `fn` should return the already-parsed `data` payload for the result, or raise.
        """
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url, timeout=self.timeout_seconds
            ) as client:
                data = await fn(client)
            latency_ms = (time.perf_counter() - start) * 1000
            result = ToolResult(
                provider=self.provider,
                operation=operation,
                status=ToolStatus.OK,
                latency_ms=latency_ms,
                data=data,
            )
        except ToolNotImplementedError as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            result = ToolResult(
                provider=self.provider,
                operation=operation,
                status=ToolStatus.NOT_IMPLEMENTED,
                latency_ms=latency_ms,
                error=str(exc) or "not implemented",
            )
        except httpx.TimeoutException as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            result = ToolResult(
                provider=self.provider,
                operation=operation,
                status=ToolStatus.TIMEOUT,
                latency_ms=latency_ms,
                error=str(exc),
            )
        except Exception as exc:  # noqa: BLE001 - deliberately broad: this is the reporting boundary
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
