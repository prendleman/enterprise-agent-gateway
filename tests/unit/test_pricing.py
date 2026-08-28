"""Unit tests for pricing catalog and cost calculation."""

from __future__ import annotations

import pytest

from agent_gateway.providers.pricing import PricingCatalog


def test_loads_pricing_yaml(pricing_catalog: PricingCatalog) -> None:
    pricing = pricing_catalog.get("fake", "fake-mini")
    assert pricing is not None
    assert pricing.input_per_1m == 0.05
    assert pricing.output_per_1m == 0.10


def test_calculates_cost_from_token_counts(pricing_catalog: PricingCatalog) -> None:
    cost = pricing_catalog.cost_usd(
        provider="fake",
        model="fake-mini",
        input_tokens=1_000_000,
        output_tokens=500_000,
    )
    assert cost == pytest.approx(0.05 + 0.05)


def test_quality_score_from_catalog(pricing_catalog: PricingCatalog) -> None:
    score = pricing_catalog.quality_score("fake-openai", "fake-openai-mini")
    assert score == pytest.approx(0.72)
