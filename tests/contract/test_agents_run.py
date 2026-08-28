"""Contract tests for POST /v1/agents/run."""

import pytest
from httpx import AsyncClient
from tests.conftest import KEY_ANALYST_NORTHSTAR, KEY_EMPLOYEE_NORTHSTAR, KEY_FM_NORTHSTAR


@pytest.mark.asyncio
async def test_agents_run_requires_api_key(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/agents/run",
        json={
            "conversation_id": "c1",
            "query": "What is the safety policy?",
        },
    )
    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")


@pytest.mark.asyncio
async def test_agents_run_response_contract(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/agents/run",
        headers={"X-API-Key": KEY_ANALYST_NORTHSTAR},
        json={
            "conversation_id": "demo-conversation-001",
            "query": "Summarize safety policies for our portfolio",
            "routing_policy": "balanced",
            "max_cost_usd": 0.05,
            "metadata": {"source": "contract-test"},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "request_id" in body
    assert isinstance(body["answer"], str)
    assert isinstance(body["citations"], list)
    assert isinstance(body["tool_calls"], list)
    assert body["provider_used"]
    assert body["model_used"]
    assert isinstance(body["latency_ms"], int)
    assert "usage" in body
    assert "trace_id" in body


@pytest.mark.asyncio
async def test_metrics_endpoint(client: AsyncClient) -> None:
    await client.post(
        "/v1/agents/run",
        headers={"X-API-Key": KEY_EMPLOYEE_NORTHSTAR},
        json={"conversation_id": "c1", "query": "What is the safety policy?"},
    )
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "agent_requests_total" in response.text


@pytest.mark.asyncio
async def test_employee_denied_work_order_tool(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/agents/run",
        headers={"X-API-Key": KEY_EMPLOYEE_NORTHSTAR},
        json={
            "conversation_id": "c2",
            "query": "List open safety critical work orders at Lakeshore Tower",
        },
    )
    assert response.status_code == 200
    body = response.json()
    denied = [call for call in body["tool_calls"] if call["name"] == "search_work_orders"]
    assert denied
    assert denied[0]["status"] == "denied"
    assert any(d["reason"] == "tool_denied_role" for d in body["policy_decisions"])


@pytest.mark.asyncio
async def test_facilities_manager_can_plan_write_tool(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/agents/run",
        headers={"X-API-Key": KEY_FM_NORTHSTAR},
        json={
            "conversation_id": "c3",
            "query": "create maintenance request for broken elevator at building bldg-001",
        },
    )
    assert response.status_code == 200
    body = response.json()
    names = {call["name"] for call in body["tool_calls"]}
    assert "create_maintenance_request" in names
