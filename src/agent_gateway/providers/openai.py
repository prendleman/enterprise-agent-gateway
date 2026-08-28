"""OpenAI provider adapter."""

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


class OpenAIProvider(LLMProvider):
    """Adapter for the OpenAI chat completions API."""

    def __init__(
        self,
        *,
        api_key: str | None,
        pricing: PricingCatalog | None = None,
        default_model: str = "gpt-4o-mini",
    ) -> None:
        self._api_key = api_key
        self._pricing = pricing
        self._default_model = default_model
        self._capabilities = ProviderCapabilities(
            name="openai",
            display_name="OpenAI",
            models=["gpt-4o-mini", "gpt-4o"],
            default_model=default_model,
            quality_score=0.85,
            enabled=api_key is not None,
        )

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def is_configured(self) -> bool:
        return self._api_key is not None

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        if not self.is_configured():
            raise PermanentProviderError("OpenAI API key is not configured", provider="openai")

        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise PermanentProviderError(
                "openai package is not installed",
                provider="openai",
            ) from exc

        client = AsyncOpenAI(api_key=self._api_key)
        try:
            response = await client.chat.completions.create(
                model=request.model,
                messages=[m.model_dump() for m in request.messages],
                max_tokens=request.max_tokens,
                temperature=request.temperature,
            )
        except Exception as exc:
            raise _map_openai_error(exc) from exc

        choice = response.choices[0]
        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0
        cost = None
        if self._pricing is not None:
            cost = self._pricing.cost_usd(
                provider="openai",
                model=request.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        return CompletionResponse(
            content=choice.message.content or "",
            model=request.model,
            provider="openai",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            finish_reason=choice.finish_reason or "stop",
            cost_usd=cost,
        )

    async def health_check(self) -> ProviderHealthStatus:
        if not self.is_configured():
            return ProviderHealthStatus.UNAVAILABLE
        return ProviderHealthStatus.HEALTHY


def _map_openai_error(exc: Exception) -> TransientProviderError | PermanentProviderError:
    name = exc.__class__.__name__
    transient_names = {
        "RateLimitError",
        "APITimeoutError",
        "APIConnectionError",
        "InternalServerError",
    }
    if name in transient_names:
        return TransientProviderError(str(exc), provider="openai")
    return PermanentProviderError(str(exc), provider="openai")
