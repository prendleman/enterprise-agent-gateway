"""Anthropic provider adapter."""

from __future__ import annotations

from agent_gateway.providers.base import (
    CompletionRequest,
    CompletionResponse,
    LLMProvider,
    PermanentProviderError,
    ProviderCapabilities,
    ProviderHealthStatus,
    TransientProviderError,
)
from agent_gateway.providers.pricing import PricingCatalog


class AnthropicProvider(LLMProvider):
    """Adapter for the Anthropic messages API."""

    def __init__(
        self,
        *,
        api_key: str | None,
        pricing: PricingCatalog | None = None,
        default_model: str = "claude-3-5-haiku-latest",
    ) -> None:
        self._api_key = api_key
        self._pricing = pricing
        self._default_model = default_model
        self._capabilities = ProviderCapabilities(
            name="anthropic",
            display_name="Anthropic",
            models=["claude-3-5-haiku-latest", "claude-3-5-sonnet-latest"],
            default_model=default_model,
            quality_score=0.88,
            enabled=api_key is not None,
        )

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def is_configured(self) -> bool:
        return self._api_key is not None

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        if not self.is_configured():
            raise PermanentProviderError(
                "Anthropic API key is not configured",
                provider="anthropic",
            )

        try:
            from anthropic import AsyncAnthropic
        except ImportError as exc:
            raise PermanentProviderError(
                "anthropic package is not installed",
                provider="anthropic",
            ) from exc

        system_parts = [m.content for m in request.messages if m.role == "system"]
        user_messages = [
            {"role": m.role, "content": m.content}
            for m in request.messages
            if m.role in {"user", "assistant"}
        ]
        client = AsyncAnthropic(api_key=self._api_key)
        try:
            response = await client.messages.create(
                model=request.model,
                max_tokens=request.max_tokens or 1024,
                system="\n".join(system_parts) if system_parts else None,
                messages=user_messages,
                temperature=request.temperature,
            )
        except Exception as exc:
            raise _map_anthropic_error(exc) from exc

        content = ""
        if response.content:
            content = response.content[0].text if hasattr(response.content[0], "text") else ""
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = None
        if self._pricing is not None:
            cost = self._pricing.cost_usd(
                provider="anthropic",
                model=request.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        return CompletionResponse(
            content=content,
            model=request.model,
            provider="anthropic",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            finish_reason=response.stop_reason or "stop",
            cost_usd=cost,
        )

    async def health_check(self) -> ProviderHealthStatus:
        if not self.is_configured():
            return ProviderHealthStatus.UNAVAILABLE
        return ProviderHealthStatus.HEALTHY


def _map_anthropic_error(exc: Exception) -> TransientProviderError | PermanentProviderError:
    name = exc.__class__.__name__
    transient_names = {
        "RateLimitError",
        "APITimeoutError",
        "APIConnectionError",
        "InternalServerError",
        "OverloadedError",
    }
    if name in transient_names:
        return TransientProviderError(str(exc), provider="anthropic")
    return PermanentProviderError(str(exc), provider="anthropic")
