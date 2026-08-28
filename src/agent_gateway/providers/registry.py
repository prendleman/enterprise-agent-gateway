"""Provider registry and factory."""

from __future__ import annotations

from pathlib import Path

from agent_gateway.config.models import load_models_config
from agent_gateway.config.settings import Settings
from agent_gateway.providers.anthropic import AnthropicProvider
from agent_gateway.providers.base import LLMProvider
from agent_gateway.providers.fake import FakeProvider
from agent_gateway.providers.openai import OpenAIProvider
from agent_gateway.providers.pricing import PricingCatalog


class ProviderRegistry:
    """Registry of configured LLM providers keyed by name."""

    def __init__(
        self,
        providers: dict[str, LLMProvider],
        *,
        pricing: PricingCatalog | None = None,
    ) -> None:
        self._providers = providers
        self.pricing = pricing

    def get(self, name: str) -> LLMProvider | None:
        return self._providers.get(name)

    def all(self) -> list[LLMProvider]:
        return list(self._providers.values())

    def available(self) -> list[LLMProvider]:
        return [p for p in self._providers.values() if p.capabilities.enabled]

    def names(self) -> list[str]:
        return list(self._providers.keys())


def build_registry(settings: Settings | None = None) -> ProviderRegistry:
    """Construct the default provider registry from settings."""
    cfg = settings or Settings()
    pricing_path = Path(cfg.model_pricing_path)
    pricing = PricingCatalog.from_yaml(pricing_path) if pricing_path.exists() else None
    models_cfg = load_models_config(Path(cfg.models_config_path))
    openai_default = cfg.openai_default_model or (
        models_cfg.openai.default_model if models_cfg else "gpt-4o-mini"
    )
    openai_models = models_cfg.openai.supported_models if models_cfg else ["gpt-4o-mini", "gpt-4o"]
    anthropic_default = cfg.anthropic_default_model or (
        models_cfg.anthropic.default_model if models_cfg else "claude-3-5-haiku-latest"
    )
    anthropic_models = (
        models_cfg.anthropic.supported_models
        if models_cfg
        else ["claude-3-5-haiku-latest", "claude-3-5-sonnet-latest"]
    )

    providers: dict[str, LLMProvider] = {}

    if cfg.is_demo or cfg.use_fake_providers:
        providers["fake-openai"] = FakeProvider(
            name="fake-openai",
            display_name="Fake OpenAI",
            models=["fake-openai-mini"],
            default_model="fake-openai-mini",
            quality_score=0.72,
        )
        providers["fake-anthropic"] = FakeProvider(
            name="fake-anthropic",
            display_name="Fake Anthropic",
            models=["fake-anthropic-mini"],
            default_model="fake-anthropic-mini",
            quality_score=0.78,
        )
        providers["fake"] = FakeProvider(
            name="fake",
            display_name="Fake Default",
            models=["fake-mini", "fake-pro"],
            default_model="fake-mini",
            quality_score=0.50,
        )
    else:
        openai = OpenAIProvider(
            api_key=cfg.openai_api_key,
            pricing=pricing,
            default_model=openai_default,
            supported_models=openai_models,
        )
        if openai.is_configured():
            providers["openai"] = openai

        anthropic = AnthropicProvider(
            api_key=cfg.anthropic_api_key,
            pricing=pricing,
            default_model=anthropic_default,
            supported_models=anthropic_models,
        )
        if anthropic.is_configured():
            providers["anthropic"] = anthropic

        if not providers:
            providers["fake"] = FakeProvider(name="fake")

    return ProviderRegistry(providers, pricing=pricing)
