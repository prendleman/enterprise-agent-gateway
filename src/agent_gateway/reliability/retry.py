"""Retry helpers built on tenacity."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from agent_gateway.providers.base import ProviderError

MAX_RETRIES = 2  # two retries after the initial attempt (three total tries)


def _is_transient(exc: BaseException) -> bool:
    return isinstance(exc, ProviderError) and exc.transient


async def with_retries[T](
    operation: Callable[[], Awaitable[T]],
    *,
    max_retries: int = MAX_RETRIES,
) -> T:
    """Execute *operation* with exponential backoff and jitter on transient errors."""
    attempts = max_retries + 1
    retrying = AsyncRetrying(
        stop=stop_after_attempt(attempts),
        wait=wait_exponential_jitter(initial=0.25, max=2.0),
        retry=retry_if_exception(_is_transient),
        reraise=True,
    )
    try:
        async for attempt in retrying:
            with attempt:
                return await operation()
    except RetryError as exc:
        raise exc.last_attempt.exception() from exc
    raise RuntimeError("retry loop exited without result")


class RetriesExhaustedError(ProviderError):
    """All retry attempts failed."""

    transient = False

    def __init__(self, message: str, *, provider: str | None = None) -> None:
        super().__init__(message, provider=provider)
