"""Unit tests for cumulative request-level cost budgeting."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agent_gateway.agent.loop import AgentLoop, CostCeilingExceededError
from agent_gateway.auth.service import AuthService
from agent_gateway.config.settings import Settings
from agent_gateway.providers.base import CompletionRequest, CompletionResponse
from agent_gateway.providers.fake import FakeProvider


def _settings() -> Settings:
    return Settings(
        demo_mode=True,
        use_fake_providers=True,
        default_max_cost_usd=0.05,
    )


def _router_with_cost_per_call(cost_per_call: float) -> MagicMock:
    fake = FakeProvider(name="fake", default_model="fake-mini")
    router = MagicMock()
    router.default_provider.return_value = fake
    router.available_providers.return_value = [fake]

    async def _complete(
        request: CompletionRequest,
        *,
        policy=None,
        preferred_provider=None,
    ) -> CompletionResponse:
        if request.metadata.get("structured") == "plan":
            content = '{"steps":[],"rationale":"unit-test plan"}'
        elif request.metadata.get("structured") == "answer":
            content = '{"answer":"Completed lookup.","citations":[]}'
        else:
            content = "initial routing acknowledgement"
        return CompletionResponse(
            content=content,
            model="fake-mini",
            provider="fake",
            input_tokens=10,
            output_tokens=10,
            finish_reason="stop",
            cost_usd=cost_per_call,
        )

    router.complete = AsyncMock(side_effect=_complete)
    return router


@pytest.mark.asyncio
async def test_cost_ceiling_fails_only_after_cumulative_usage_exceeds_budget() -> None:
    cost_per_call = 0.01
    ceiling = 0.025
    router = _router_with_cost_per_call(cost_per_call)
    loop = AgentLoop(router=router)
    auth = AuthService(_settings()).authenticate("demo-analyst-northstar")
    assert auth is not None

    with pytest.raises(CostCeilingExceededError) as exc_info:
        await loop.run(
            query="Summarize safety policies",
            auth=auth,
            request_id="cost-cumulative-fail",
            max_cost_usd=ceiling,
        )

    assert router.complete.await_count == 3
    assert cost_per_call < ceiling
    assert (cost_per_call * 2) < ceiling
    assert (cost_per_call * 3) > ceiling
    assert "cumulative" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_reported_usage_equals_sum_of_completion_costs() -> None:
    cost_per_call = 0.01
    router = _router_with_cost_per_call(cost_per_call)
    loop = AgentLoop(router=router)
    auth = AuthService(_settings()).authenticate("demo-analyst-northstar")
    assert auth is not None

    result = await loop.run(
        query="Summarize safety policies",
        auth=auth,
        request_id="cost-cumulative-success",
        max_cost_usd=1.0,
    )

    assert router.complete.await_count == 3
    assert result.usage.input_tokens == 30
    assert result.usage.output_tokens == 30
    assert result.usage.estimated_cost_usd == pytest.approx(cost_per_call * 3)
