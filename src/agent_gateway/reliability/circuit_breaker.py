"""Per-provider circuit breaker."""

from __future__ import annotations

import time
from enum import StrEnum

from agent_gateway.providers.base import CircuitOpenError, ProviderError


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Opens after consecutive transient failures; recovers after a cooldown."""

    def __init__(
        self,
        *,
        failure_threshold: int = 3,
        recovery_timeout_seconds: float = 30.0,
        name: str = "default",
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> CircuitState:
        self._maybe_transition_to_half_open()
        return self._state

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    def allow_request(self) -> bool:
        """Return True when a request may proceed."""
        return self.state != CircuitState.OPEN

    def before_call(self) -> None:
        """Raise when the circuit is open."""
        if not self.allow_request():
            raise CircuitOpenError(
                f"Circuit breaker '{self.name}' is open",
                provider=self.name,
            )

    def record_success(self) -> None:
        """Reset failure count and close the circuit."""
        self._consecutive_failures = 0
        self._opened_at = None
        self._state = CircuitState.CLOSED

    def record_failure(self, error: ProviderError) -> None:
        """Track failures; open circuit after threshold consecutive transient errors."""
        if not error.transient:
            return

        self._consecutive_failures += 1
        if self._consecutive_failures >= self.failure_threshold:
            self._state = CircuitState.OPEN
            self._opened_at = time.monotonic()

    def _maybe_transition_to_half_open(self) -> None:
        if self._state != CircuitState.OPEN or self._opened_at is None:
            return
        elapsed = time.monotonic() - self._opened_at
        if elapsed >= self.recovery_timeout_seconds:
            self._state = CircuitState.HALF_OPEN
