"""
Retry with exponential backoff for transient failures (Section 7.5).

Only retries transient errors:
  - network: httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout
  - LLM providers: openai.RateLimitError, openai.APITimeoutError,
                   openai.APIConnectionError, openai.InternalServerError
  - generic 5xx HTTP

Never retries:
  - auth errors (openai.AuthenticationError, PermissionError)
  - validation errors (ValueError, TypeError)
  - QueryRejected (analytics query guardrail)
  - 4xx (except 429 Too Many Requests)
"""
import asyncio
from typing import Any, Awaitable, Callable, TypeVar

from .audit import log_event


T = TypeVar("T")

DEFAULT_BACKOFF = (1.0, 4.0, 16.0)


def _is_transient(exc: BaseException) -> bool:
    try:
        import httpx
    except ImportError:
        httpx = None

    try:
        import openai
    except ImportError:
        openai = None

    try:
        from .postgres import QueryRejected
        if isinstance(exc, QueryRejected):
            return False
    except ImportError:
        pass

    if isinstance(exc, (ValueError, TypeError, PermissionError)):
        return False

    if httpx is not None:
        if isinstance(exc, (httpx.ConnectError, httpx.ReadTimeout,
                            httpx.ConnectTimeout, httpx.RemoteProtocolError)):
            return True
        if isinstance(exc, httpx.HTTPStatusError):
            code = exc.response.status_code
            return code >= 500 or code == 429

    if openai is not None:
        if isinstance(exc, (openai.RateLimitError, openai.APITimeoutError,
                            openai.APIConnectionError, openai.InternalServerError)):
            return True
        if isinstance(exc, (openai.AuthenticationError, openai.PermissionDeniedError,
                            openai.BadRequestError)):
            return False

    return False


async def with_retry(
    fn: Callable[..., Awaitable[T]],
    *args: Any,
    max_attempts: int = 3,
    backoff: tuple[float, ...] = DEFAULT_BACKOFF,
    tenant_id: str | None = None,
    operation: str | None = None,
    **kwargs: Any,
) -> T:
    """
    Run `fn(*args, **kwargs)`. On transient failure, sleep and retry.
    On permanent failure, raise immediately. On exhaustion, raise last exc.
    """
    op_name = operation or getattr(fn, "__name__", "unknown")
    last_exc: BaseException | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            return await fn(*args, **kwargs)
        except BaseException as exc:
            last_exc = exc
            if not _is_transient(exc):
                await log_event(
                    tenant_id=tenant_id,
                    event_type="retry.non_transient",
                    payload={
                        "operation": op_name,
                        "attempt": attempt,
                        "error": f"{type(exc).__name__}: {exc}"[:1000],
                    },
                )
                raise

            if attempt >= max_attempts:
                await log_event(
                    tenant_id=tenant_id,
                    event_type="retry.exhausted",
                    payload={
                        "operation": op_name,
                        "attempts": attempt,
                        "error": f"{type(exc).__name__}: {exc}"[:1000],
                    },
                )
                raise

            sleep_for = backoff[min(attempt - 1, len(backoff) - 1)]
            await log_event(
                tenant_id=tenant_id,
                event_type="retry.transient",
                payload={
                    "operation": op_name,
                    "attempt": attempt,
                    "sleep_seconds": sleep_for,
                    "error": f"{type(exc).__name__}: {exc}"[:1000],
                },
            )
            await asyncio.sleep(sleep_for)

    assert last_exc is not None
    raise last_exc
