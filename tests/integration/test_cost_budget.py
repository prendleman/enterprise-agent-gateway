"""Tests for cumulative request cost budgeting."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from tests.conftest import KEY_ANALYST_NORTHSTAR


@pytest.mark.asyncio
async def test_cumulative_cost_ceiling_rejects_request(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/agents/run",
        headers={"X-API-Key": KEY_ANALYST_NORTHSTAR},
        json={
            "conversation_id": "cost-ceiling",
            "query": "Summarize safety policies and open HVAC work orders",
            "max_cost_usd": 0.000001,
        },
    )
    assert response.status_code == 402
    body = response.json()
    assert "cost" in body["detail"].lower() or "ceiling" in body["detail"].lower()


@pytest.mark.asyncio
async def test_usage_reports_cumulative_tokens(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/agents/run",
        headers={"X-API-Key": KEY_ANALYST_NORTHSTAR},
        json={
            "conversation_id": "usage-total",
            "query": "What is the safety policy?",
            "max_cost_usd": 0.05,
        },
    )
    assert response.status_code == 200
    usage = response.json()["usage"]
    assert usage["input_tokens"] > 0
    assert usage["output_tokens"] > 0
    assert usage["estimated_cost_usd"] >= 0
