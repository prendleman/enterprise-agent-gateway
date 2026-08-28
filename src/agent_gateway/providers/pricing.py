"""Load model pricing and compute request cost."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ModelPricing:
    """Per-model token pricing in USD per 1M tokens."""

    provider: str
    model: str
    input_per_1m: float
    output_per_1m: float
    quality_score: float


class PricingCatalog:
    """In-memory pricing catalog sourced from YAML."""

    def __init__(self, models: dict[tuple[str, str], ModelPricing]) -> None:
        self._models = models

    @classmethod
    def from_yaml(cls, path: str | Path) -> PricingCatalog:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        models: dict[tuple[str, str], ModelPricing] = {}
        providers = data.get("providers", {})
        for provider_name, provider_cfg in providers.items():
            for model_name, model_cfg in provider_cfg.get("models", {}).items():
                models[(provider_name, model_name)] = ModelPricing(
                    provider=provider_name,
                    model=model_name,
                    input_per_1m=float(model_cfg["input_per_1m"]),
                    output_per_1m=float(model_cfg["output_per_1m"]),
                    quality_score=float(model_cfg.get("quality_score", 0.5)),
                )
        return cls(models)

    def get(self, provider: str, model: str) -> ModelPricing | None:
        return self._models.get((provider, model))

    def cost_usd(
        self,
        *,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float | None:
        pricing = self.get(provider, model)
        if pricing is None:
            return None
        input_cost = (input_tokens / 1_000_000) * pricing.input_per_1m
        output_cost = (output_tokens / 1_000_000) * pricing.output_per_1m
        return round(input_cost + output_cost, 8)

    def quality_score(self, provider: str, model: str) -> float | None:
        pricing = self.get(provider, model)
        return pricing.quality_score if pricing else None

    def cheapest_providers(self) -> list[str]:
        """Return provider names ordered by cheapest default model input rate."""
        by_provider: dict[str, float] = {}
        for (provider, _model), pricing in self._models.items():
            current = by_provider.get(provider)
            if current is None or pricing.input_per_1m < current:
                by_provider[provider] = pricing.input_per_1m
        return sorted(by_provider, key=by_provider.get)
