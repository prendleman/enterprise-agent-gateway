"""Simulate primary provider outage and verify failover."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


async def _simulate() -> dict:
    from agent_gateway.providers.base import ChatMessage, CompletionRequest, RoutingPolicy
    from agent_gateway.providers.fake import FakeProvider, permanent_error
    from agent_gateway.providers.pricing import PricingCatalog
    from agent_gateway.providers.registry import ProviderRegistry
    from agent_gateway.providers.router import ProviderRouter

    pricing = PricingCatalog.from_yaml(ROOT / "config" / "model_pricing.example.yaml")
    shared_model = "shared-eval-model"
    primary = FakeProvider(
        name="fake-openai",
        display_name="Fake OpenAI (simulated outage)",
        models=[shared_model],
        default_model=shared_model,
        quality_score=0.72,
        failure_mode=permanent_error(),
    )
    backup = FakeProvider(
        name="fake-anthropic",
        display_name="Fake Anthropic (fallback)",
        models=[shared_model],
        default_model=shared_model,
        quality_score=0.78,
    )
    registry = ProviderRegistry(
        {primary.capabilities.name: primary, backup.capabilities.name: backup},
        pricing=pricing,
    )
    router = ProviderRouter(registry)
    request = CompletionRequest(
        model=shared_model,
        messages=[ChatMessage(role="user", content="Simulated outage failover probe")],
    )

    started = datetime.now(tz=UTC)
    response = await router.complete(
        request,
        policy=RoutingPolicy.PREFERRED,
        preferred_provider="fake-openai",
    )
    finished = datetime.now(tz=UTC)

    return {
        "simulation": "provider-outage",
        "label": "SIMULATED EXERCISE — not a production incident",
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "primary_provider": "fake-openai",
        "primary_forced_failure": True,
        "fallback_provider": response.provider,
        "failover_succeeded": response.provider == "fake-anthropic",
        "primary_call_count": primary.call_count,
        "backup_call_count": backup.call_count,
        "response_model": response.model,
        "response_preview": response.content[:120],
    }


def main() -> int:
    result = asyncio.run(_simulate())
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    out_path = artifacts / "outage-simulation.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(json.dumps(result, indent=2))
    print(f"Wrote {out_path}")

    return 0 if result["failover_succeeded"] else 1


if __name__ == "__main__":
    sys.exit(main())
