"""Unit tests for provider failover behavior."""

from __future__ import annotations

import pytest

from agent_gateway.providers.base import (
    ChatMessage,
    CompletionRequest,
    RoutingPolicy,
    TransientProviderError,
)
from agent_gateway.providers.fake import FakeProvider, always_transient
from agent_gateway.providers.pricing import PricingCatalog
from agent_gateway.providers.registry import ProviderRegistry
from agent_gateway.providers.router import AllProvidersFailedError, ProviderRouter
from agent_gateway.reliability.circuit_breaker import CircuitState


def _request(model: str = "shared-model") -> CompletionRequest:
    return CompletionRequest(
        model=model,
        messages=[ChatMessage(role="user", content="Route with failover")],
    )


@pytest.mark.asyncio
async def test_failover_when_primary_retries_exhausted(
    pricing_catalog: PricingCatalog,
) -> None:
    failing = FakeProvider(
        name="primary",
        models=["shared-model"],
        default_model="shared-model",
        failure_mode=always_transient(),
    )
    backup = FakeProvider(
        name="backup",
        models=["shared-model"],
        default_model="shared-model",
        quality_score=0.5,
    )
    registry = ProviderRegistry(
        {failing.capabilities.name: failing, backup.capabilities.name: backup},
        pricing=pricing_catalog,
    )
    router = ProviderRouter(registry)

    response = await router.complete(
        _request(),
        policy=RoutingPolicy.PREFERRED,
        preferred_provider="primary",
    )

    assert response.provider == "backup"
    assert failing.call_count == 3


@pytest.mark.asyncio
async def test_skips_provider_when_circuit_open(
    pricing_catalog: PricingCatalog,
) -> None:
    failing = FakeProvider(
        name="primary",
        models=["shared-model"],
        default_model="shared-model",
        failure_mode=always_transient(),
    )
    backup = FakeProvider(
        name="backup",
        models=["shared-model"],
        default_model="shared-model",
    )
    registry = ProviderRegistry(
        {failing.capabilities.name: failing, backup.capabilities.name: backup},
        pricing=pricing_catalog,
    )
    router = ProviderRouter(registry)
    breaker = router.circuit_breaker_for("primary")
    error = TransientProviderError("timeout", provider="primary")
    for _ in range(3):
        breaker.record_failure(error)
    assert breaker.state == CircuitState.OPEN

    response = await router.complete(
        _request(),
        policy=RoutingPolicy.PREFERRED,
        preferred_provider="primary",
    )

    assert response.provider == "backup"
    assert failing.call_count == 0


@pytest.mark.asyncio
async def test_all_providers_failed_raises(
    pricing_catalog: PricingCatalog,
) -> None:
    failing_a = FakeProvider(
        name="a",
        models=["shared-model"],
        failure_mode=always_transient(),
    )
    failing_b = FakeProvider(
        name="b",
        models=["shared-model"],
        failure_mode=always_transient(),
    )
    registry = ProviderRegistry(
        {failing_a.capabilities.name: failing_a, failing_b.capabilities.name: failing_b},
        pricing=pricing_catalog,
    )
    router = ProviderRouter(registry)

    with pytest.raises(AllProvidersFailedError):
        await router.complete(_request(), policy=RoutingPolicy.BALANCED)
