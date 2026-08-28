"""Deterministic fake provider for demo mode and unit tests."""

from __future__ import annotations

import hashlib
from collections.abc import Callable

from agent_gateway.providers.base import (
    CompletionRequest,
    CompletionResponse,
    LLMProvider,
    PermanentProviderError,
    ProviderCapabilities,
    ProviderHealthStatus,
    TransientProviderError,
)


class FakeProvider(LLMProvider):
    """Deterministic provider that never calls external APIs."""

    def __init__(
        self,
        *,
        name: str = "fake",
        display_name: str | None = None,
        models: list[str] | None = None,
        default_model: str | None = None,
        quality_score: float = 0.5,
        enabled: bool = True,
        failure_mode: Callable[[CompletionRequest, int], Exception | None] | None = None,
        input_tokens_per_char: float = 0.25,
        output_tokens: int = 32,
    ) -> None:
        model_list = models or ["fake-mini", "fake-pro"]
        resolved_default = default_model or model_list[0]
        self._capabilities = ProviderCapabilities(
            name=name,
            display_name=display_name or f"Fake ({name})",
            models=model_list,
            default_model=resolved_default,
            quality_score=quality_score,
            enabled=enabled,
        )
        self._failure_mode = failure_mode
        self._call_count = 0
        self._input_tokens_per_char = input_tokens_per_char
        self._output_tokens = output_tokens

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    @property
    def call_count(self) -> int:
        return self._call_count

    def reset_call_count(self) -> None:
        self._call_count = 0

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        self._call_count += 1
        if self._failure_mode is not None:
            error = self._failure_mode(request, self._call_count)
            if error is not None:
                raise error

        prompt = "\n".join(f"{m.role}: {m.content}" for m in request.messages)
        digest = hashlib.sha256(prompt.encode()).hexdigest()[:12]
        input_tokens = max(1, int(len(prompt) * self._input_tokens_per_char))
        content = f"[{self._capabilities.name}/{request.model}] deterministic response ({digest})"
        return CompletionResponse(
            content=content,
            model=request.model,
            provider=self._capabilities.name,
            input_tokens=input_tokens,
            output_tokens=self._output_tokens,
            finish_reason="stop",
        )

    async def health_check(self) -> ProviderHealthStatus:
        if not self._capabilities.enabled:
            return ProviderHealthStatus.UNAVAILABLE
        return ProviderHealthStatus.HEALTHY

    def is_configured(self) -> bool:
        return True


def transient_failures_before_success(
    count: int,
) -> Callable[[CompletionRequest, int], Exception | None]:
    """Fail with transient errors for the first *count* calls, then succeed."""

    def _handler(_request: CompletionRequest, call: int) -> Exception | None:
        if call <= count:
            return TransientProviderError("simulated transient failure", provider="fake")
        return None

    return _handler


def always_transient() -> Callable[[CompletionRequest, int], Exception | None]:
    """Always raise a transient error."""

    def _handler(_request: CompletionRequest, _call: int) -> Exception | None:
        return TransientProviderError("simulated transient failure", provider="fake")

    return _handler


def permanent_error() -> Callable[[CompletionRequest, int], Exception | None]:
    """Always raise a permanent error."""

    def _handler(_request: CompletionRequest, _call: int) -> Exception | None:
        return PermanentProviderError("simulated permanent failure", provider="fake")

    return _handler
