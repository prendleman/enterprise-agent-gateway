"""Unit tests for provider routing policies."""

from __future__ import annotations

import pytest

from agent_gateway.providers.base import ChatMessage, CompletionRequest, RoutingPolicy
from agent_gateway.providers.fake import FakeProvider
from agent_gateway.providers.pricing import PricingCatalog
from agent_gateway.providers.registry import ProviderRegistry
from agent_gateway.providers.router import ProviderRouter


def _request(model: str = "fake-openai-mini") -> CompletionRequest:
    return CompletionRequest(
        model=model,
        messages=[ChatMessage(role="user", content="Summarize lease abstract")],
    )


@pytest.mark.asyncio
async def test_preferred_policy_uses_preferred_provider(
    fake_registry: ProviderRegistry,
) -> None:
    router = ProviderRouter(fake_registry)
    response = await router.complete(
        _request("fake-anthropic-mini"),
        policy=RoutingPolicy.PREFERRED,
        preferred_provider="fake-anthropic",
    )
    assert response.provider == "fake-anthropic"


@pytest.mark.asyncio
async def test_quality_policy_prefers_higher_quality_provider(
    pricing_catalog: PricingCatalog,
) -> None:
    low = FakeProvider(
        name="low-quality",
        models=["shared-model"],
        default_model="shared-model",
        quality_score=0.2,
    )
    high = FakeProvider(
        name="high-quality",
        models=["shared-model"],
        default_model="shared-model",
        quality_score=0.95,
    )
    registry = ProviderRegistry(
        {low.capabilities.name: low, high.capabilities.name: high},
        pricing=pricing_catalog,
    )
    router = ProviderRouter(registry)

    response = await router.complete(
        _request("shared-model"),
        policy=RoutingPolicy.QUALITY,
    )
    assert response.provider == "high-quality"


@pytest.mark.asyncio
async def test_cost_policy_prefers_cheaper_provider(
    pricing_catalog: PricingCatalog,
) -> None:
    expensive = FakeProvider(
        name="anthropic",
        models=["claude-3-5-haiku-latest"],
        default_model="claude-3-5-haiku-latest",
        quality_score=0.88,
    )
    cheap = FakeProvider(
        name="openai",
        models=["gpt-4o-mini"],
        default_model="gpt-4o-mini",
        quality_score=0.72,
    )
    registry = ProviderRegistry(
        {expensive.capabilities.name: expensive, cheap.capabilities.name: cheap},
        pricing=pricing_catalog,
    )
    router = ProviderRouter(registry)

    response = await router.complete(
        CompletionRequest(
            model="gpt-4o-mini",
            messages=[ChatMessage(role="user", content="hello")],
        ),
        policy=RoutingPolicy.COST,
    )
    assert response.provider == "openai"


@pytest.mark.asyncio
async def test_balanced_policy_returns_deterministic_response(
    router: ProviderRouter,
) -> None:
    response = await router.complete(_request(), policy=RoutingPolicy.BALANCED)
    assert response.content.startswith("[fake-openai/fake-openai-mini]")
    assert response.cost_usd is not None
    assert response.cost_usd > 0
