"""Provider routing with policies, retries, circuit breaking, and failover."""

from __future__ import annotations

import structlog

from agent_gateway.observability.metrics import AGENT_PROVIDER_FAILOVERS_TOTAL
from agent_gateway.providers.base import (
    CircuitOpenError,
    CompletionRequest,
    CompletionResponse,
    LLMProvider,
    ProviderError,
    RoutingPolicy,
)
from agent_gateway.providers.registry import ProviderRegistry
from agent_gateway.reliability.circuit_breaker import CircuitBreaker
from agent_gateway.reliability.retry import RetriesExhaustedError, with_retries

logger = structlog.get_logger(__name__)


class AllProvidersFailedError(ProviderError):
    """Every candidate provider failed or was unavailable."""

    transient = False


class ProviderRouter:
    """Route completion requests across providers with reliability controls."""

    def __init__(
        self,
        registry: ProviderRegistry,
        *,
        circuit_breakers: dict[str, CircuitBreaker] | None = None,
        max_retries: int = 2,
    ) -> None:
        self._registry = registry
        self._pricing = registry.pricing
        self._circuit_breakers = circuit_breakers or {}
        self._max_retries = max_retries

    def circuit_breaker_for(self, provider_name: str) -> CircuitBreaker:
        if provider_name not in self._circuit_breakers:
            self._circuit_breakers[provider_name] = CircuitBreaker(name=provider_name)
        return self._circuit_breakers[provider_name]

    def available_providers(self) -> list[LLMProvider]:
        return self._registry.available()

    def get_provider(self, name: str) -> LLMProvider | None:
        return self._registry.get(name)

    def default_provider(self) -> LLMProvider:
        providers = self.available_providers()
        if not providers:
            raise AllProvidersFailedError("No providers are registered")
        return providers[0]

    async def complete(
        self,
        request: CompletionRequest,
        *,
        policy: RoutingPolicy = RoutingPolicy.BALANCED,
        preferred_provider: str | None = None,
    ) -> CompletionResponse:
        candidates = self._order_providers(
            policy=policy,
            model=request.model,
            preferred_provider=preferred_provider,
        )
        if not candidates:
            raise AllProvidersFailedError("No providers are registered")

        errors: list[str] = []
        attempted: list[str] = []
        for provider in candidates:
            name = provider.capabilities.name
            breaker = self.circuit_breaker_for(name)
            if not breaker.allow_request():
                errors.append(f"{name}: circuit open")
                continue

            try:
                response = await self._execute_with_reliability(provider, request, breaker)
                response.cost_usd = self._calculate_cost(response)
                if attempted:
                    AGENT_PROVIDER_FAILOVERS_TOTAL.labels(
                        from_provider=attempted[-1],
                        to_provider=name,
                    ).inc()
                return response
            except CircuitOpenError:
                errors.append(f"{name}: circuit open")
                attempted.append(name)
            except RetriesExhaustedError as exc:
                errors.append(f"{name}: retries exhausted ({exc})")
                attempted.append(name)
            except ProviderError as exc:
                errors.append(f"{name}: {exc}")
                attempted.append(name)

        raise AllProvidersFailedError(
            "All providers failed: " + "; ".join(errors),
        )

    async def _execute_with_reliability(
        self,
        provider: LLMProvider,
        request: CompletionRequest,
        breaker: CircuitBreaker,
    ) -> CompletionResponse:
        name = provider.capabilities.name

        async def _call() -> CompletionResponse:
            breaker.before_call()
            try:
                response = await provider.complete(request)
            except ProviderError as exc:
                breaker.record_failure(exc)
                raise
            else:
                breaker.record_success()
                return response

        try:
            return await with_retries(_call, max_retries=self._max_retries)
        except ProviderError as exc:
            if exc.transient:
                raise RetriesExhaustedError(
                    f"Retries exhausted for provider '{name}'",
                    provider=name,
                ) from exc
            raise

    def _order_providers(
        self,
        *,
        policy: RoutingPolicy,
        model: str,
        preferred_provider: str | None,
    ) -> list[LLMProvider]:
        providers = [p for p in self._registry.available() if model in p.capabilities.models]
        if not providers:
            providers = list(self._registry.available())

        if policy == RoutingPolicy.PREFERRED and preferred_provider:
            preferred = self._registry.get(preferred_provider)
            if preferred is not None and preferred.capabilities.enabled:
                rest = [p for p in providers if p.capabilities.name != preferred_provider]
                return [preferred, *rest]

        if policy == RoutingPolicy.QUALITY:
            return sorted(
                providers,
                key=lambda p: self._quality_score(p, model),
                reverse=True,
            )

        if policy == RoutingPolicy.COST:
            return sorted(providers, key=lambda p: self._cost_score(p, model))

        # balanced: interleave quality and cost
        quality_order = sorted(
            providers,
            key=lambda p: self._quality_score(p, model),
            reverse=True,
        )
        cost_order = sorted(providers, key=lambda p: self._cost_score(p, model))
        balanced: list[LLMProvider] = []
        seen: set[str] = set()
        for left, right in zip(quality_order, cost_order, strict=False):
            for candidate in (left, right):
                name = candidate.capabilities.name
                if name not in seen:
                    balanced.append(candidate)
                    seen.add(name)
        for provider in providers:
            if provider.capabilities.name not in seen:
                balanced.append(provider)
        return balanced

    def _quality_score(self, provider: LLMProvider, model: str) -> float:
        if self._pricing is not None:
            score = self._pricing.quality_score(provider.capabilities.name, model)
            if score is not None:
                return score
        return provider.capabilities.quality_score

    def _cost_score(self, provider: LLMProvider, model: str) -> float:
        if self._pricing is not None:
            pricing = self._pricing.get(provider.capabilities.name, model)
            if pricing is not None:
                return pricing.input_per_1m + pricing.output_per_1m
        return 1.0 / max(provider.capabilities.quality_score, 0.01)

    def _calculate_cost(self, response: CompletionResponse) -> float | None:
        if self._pricing is None:
            return response.cost_usd
        return self._pricing.cost_usd(
            provider=response.provider,
            model=response.model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )
