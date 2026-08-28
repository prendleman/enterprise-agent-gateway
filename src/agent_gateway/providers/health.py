"""Aggregate provider health reporting."""

from __future__ import annotations

from pydantic import BaseModel

from agent_gateway.providers.base import LLMProvider, ProviderHealthStatus
from agent_gateway.providers.registry import ProviderRegistry
from agent_gateway.reliability.circuit_breaker import CircuitBreaker, CircuitState


class ProviderHealthReport(BaseModel):
    """Health snapshot for a single provider."""

    provider: str
    configured: bool
    enabled: bool
    health: ProviderHealthStatus
    circuit_state: CircuitState


class ProviderHealthService:
    """Collect health and circuit breaker state for all providers."""

    def __init__(
        self,
        registry: ProviderRegistry,
        circuit_breakers: dict[str, CircuitBreaker] | None = None,
    ) -> None:
        self._registry = registry
        self._circuit_breakers = circuit_breakers or {}

    async def check_provider(self, provider: LLMProvider) -> ProviderHealthReport:
        name = provider.capabilities.name
        breaker = self._circuit_breakers.get(name)
        return ProviderHealthReport(
            provider=name,
            configured=provider.is_configured(),
            enabled=provider.capabilities.enabled,
            health=await provider.health_check(),
            circuit_state=breaker.state if breaker else CircuitState.CLOSED,
        )

    async def check_all(self) -> list[ProviderHealthReport]:
        reports: list[ProviderHealthReport] = []
        for provider in self._registry.all():
            reports.append(await self.check_provider(provider))
        return reports
