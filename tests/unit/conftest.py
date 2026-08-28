"""Shared fixtures for provider unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_gateway.providers.fake import FakeProvider
from agent_gateway.providers.pricing import PricingCatalog
from agent_gateway.providers.registry import ProviderRegistry
from agent_gateway.providers.router import ProviderRouter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRICING_PATH = PROJECT_ROOT / "config" / "model_pricing.example.yaml"


@pytest.fixture
def pricing_catalog() -> PricingCatalog:
    return PricingCatalog.from_yaml(PRICING_PATH)


@pytest.fixture
def fake_openai() -> FakeProvider:
    return FakeProvider(
        name="fake-openai",
        models=["fake-openai-mini"],
        default_model="fake-openai-mini",
        quality_score=0.72,
    )


@pytest.fixture
def fake_anthropic() -> FakeProvider:
    return FakeProvider(
        name="fake-anthropic",
        models=["fake-anthropic-mini"],
        default_model="fake-anthropic-mini",
        quality_score=0.78,
    )


@pytest.fixture
def fake_registry(
    fake_openai: FakeProvider,
    fake_anthropic: FakeProvider,
    pricing_catalog: PricingCatalog,
) -> ProviderRegistry:
    return ProviderRegistry(
        {
            fake_openai.capabilities.name: fake_openai,
            fake_anthropic.capabilities.name: fake_anthropic,
        },
        pricing=pricing_catalog,
    )


@pytest.fixture
def router(fake_registry: ProviderRegistry) -> ProviderRouter:
    return ProviderRouter(fake_registry)
