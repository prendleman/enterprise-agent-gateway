"""Unit tests for retry behavior."""

from __future__ import annotations

import pytest

from agent_gateway.providers.base import PermanentProviderError, TransientProviderError
from agent_gateway.reliability.retry import with_retries


@pytest.mark.asyncio
async def test_retries_transient_errors_up_to_two_times() -> None:
    attempts = {"count": 0}

    async def flaky() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise TransientProviderError("temporary", provider="fake")
        return "ok"

    result = await with_retries(flaky, max_retries=2)
    assert result == "ok"
    assert attempts["count"] == 3


@pytest.mark.asyncio
async def test_does_not_retry_permanent_errors() -> None:
    attempts = {"count": 0}

    async def fail() -> str:
        attempts["count"] += 1
        raise PermanentProviderError("invalid", provider="fake")

    with pytest.raises(PermanentProviderError):
        await with_retries(fail, max_retries=2)

    assert attempts["count"] == 1


@pytest.mark.asyncio
async def test_raises_after_retries_exhausted() -> None:
    async def always_fail() -> str:
        raise TransientProviderError("temporary", provider="fake")

    with pytest.raises(TransientProviderError):
        await with_retries(always_fail, max_retries=2)
