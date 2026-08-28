"""Unit tests for circuit breaker behavior."""

from __future__ import annotations

import time

import pytest

from agent_gateway.providers.base import PermanentProviderError, TransientProviderError
from agent_gateway.reliability.circuit_breaker import CircuitBreaker, CircuitState


def test_circuit_stays_closed_on_success() -> None:
    breaker = CircuitBreaker(name="test")
    breaker.record_success()
    assert breaker.state == CircuitState.CLOSED
    assert breaker.allow_request() is True


def test_circuit_opens_after_three_transient_failures() -> None:
    breaker = CircuitBreaker(name="test", failure_threshold=3)
    error = TransientProviderError("timeout", provider="test")

    breaker.record_failure(error)
    breaker.record_failure(error)
    assert breaker.state == CircuitState.CLOSED

    breaker.record_failure(error)
    assert breaker.state == CircuitState.OPEN
    assert breaker.allow_request() is False


def test_permanent_failures_do_not_open_circuit() -> None:
    breaker = CircuitBreaker(name="test", failure_threshold=3)
    error = PermanentProviderError("bad request", provider="test")

    for _ in range(5):
        breaker.record_failure(error)

    assert breaker.state == CircuitState.CLOSED
    assert breaker.consecutive_failures == 0


def test_success_resets_failure_count() -> None:
    breaker = CircuitBreaker(name="test", failure_threshold=3)
    error = TransientProviderError("timeout", provider="test")

    breaker.record_failure(error)
    breaker.record_failure(error)
    breaker.record_success()

    breaker.record_failure(error)
    assert breaker.state == CircuitState.CLOSED


def test_circuit_recovers_after_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    breaker = CircuitBreaker(
        name="test",
        failure_threshold=3,
        recovery_timeout_seconds=30.0,
    )
    error = TransientProviderError("timeout", provider="test")
    now = {"value": 1000.0}
    monkeypatch.setattr(time, "monotonic", lambda: now["value"])

    for _ in range(3):
        breaker.record_failure(error)
    assert breaker.state == CircuitState.OPEN

    now["value"] += 29.0
    assert breaker.state == CircuitState.OPEN

    now["value"] += 1.0
    assert breaker.state == CircuitState.HALF_OPEN
    assert breaker.allow_request() is True

    breaker.record_success()
    assert breaker.state == CircuitState.CLOSED
