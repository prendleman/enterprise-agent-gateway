"""Load provider model configuration from YAML."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ProviderModelConfig:
    default_model: str
    supported_models: list[str]


@dataclass(frozen=True)
class ModelsConfig:
    openai: ProviderModelConfig
    anthropic: ProviderModelConfig


def load_models_config(path: Path) -> ModelsConfig | None:
    if not path.is_file():
        return None
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    openai_raw = raw.get("openai", {})
    anthropic_raw = raw.get("anthropic", {})
    return ModelsConfig(
        openai=ProviderModelConfig(
            default_model=str(openai_raw.get("default_model", "gpt-4o-mini")),
            supported_models=list(openai_raw.get("supported_models") or ["gpt-4o-mini"]),
        ),
        anthropic=ProviderModelConfig(
            default_model=str(anthropic_raw.get("default_model", "claude-3-5-haiku-latest")),
            supported_models=list(
                anthropic_raw.get("supported_models") or ["claude-3-5-haiku-latest"]
            ),
        ),
    )
