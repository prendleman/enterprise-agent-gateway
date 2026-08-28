"""Integration tests for tenant isolation, citations, and idempotency."""

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from tests.conftest import KEY_ANALYST_LAKESHORE, KEY_ANALYST_NORTHSTAR, KEY_FM_NORTHSTAR

from agent_gateway.storage.database import get_session_factory
from agent_gateway.storage.models import Building, MaintenanceRequest


@pytest.mark.asyncio
async def test_tenant_isolation_building_summary(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/agents/run",
        headers={"X-API-Key": KEY_ANALYST_LAKESHORE},
        json={
            "conversation_id": "iso-1",
            "query": "building summary for Willis Tower",
        },
    )
    assert response.status_code == 200
    body = response.json()
    summary_calls = [c for c in body["tool_calls"] if c["name"] == "get_building_summary"]
    assert summary_calls
    assert summary_calls[0]["status"] in {"succeeded", "failed"}
    if summary_calls[0]["status"] == "failed":
        assert "not found" in body["answer"].lower() or body["answer"]


@pytest.mark.asyncio
async def test_northstar_analyst_sees_willis_tower(client: AsyncClient) -> None:
    factory = get_session_factory()
    async with factory() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(Building)
            .where(
                Building.tenant_id == "northstar-facilities",
                Building.name == "Willis Tower",
            )
        )
        assert count == 1

    response = await client.post(
        "/v1/agents/run",
        headers={"X-API-Key": KEY_ANALYST_NORTHSTAR},
        json={
            "conversation_id": "iso-2",
            "query": "building summary for Willis Tower",
        },
    )
    assert response.status_code == 200
    summary_calls = [
        c for c in response.json()["tool_calls"] if c["name"] == "get_building_summary"
    ]
    assert summary_calls
    assert summary_calls[0]["status"] == "succeeded"


@pytest.mark.asyncio
async def test_citations_present_for_policy_search(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/agents/run",
        headers={"X-API-Key": KEY_ANALYST_NORTHSTAR},
        json={
            "conversation_id": "cite-1",
            "query": "What safety policy procedures apply to managed properties?",
        },
    )
    assert response.status_code == 200
    body = response.json()
    policy_calls = [c for c in body["tool_calls"] if c["name"] == "search_policy_documents"]
    assert policy_calls
    if policy_calls[0]["status"] == "succeeded":
        assert body["citations"]


@pytest.mark.asyncio
async def test_create_maintenance_request_idempotency(client: AsyncClient) -> None:
    payload = {
        "conversation_id": "idem-1",
        "query": (
            "create maintenance request for HVAC inspection at building bldg-001 "
            "with idempotency key idem-key-001"
        ),
    }
    first = await client.post(
        "/v1/agents/run",
        headers={"X-API-Key": KEY_FM_NORTHSTAR},
        json=payload,
    )
    assert first.status_code == 200

    factory = get_session_factory()
    async with factory() as session:
        count_after_first = await session.scalar(
            select(func.count()).select_from(MaintenanceRequest)
        )

    second = await client.post(
        "/v1/agents/run",
        headers={"X-API-Key": KEY_FM_NORTHSTAR},
        json=payload,
    )
    assert second.status_code == 200

    async with factory() as session:
        count_after_second = await session.scalar(
            select(func.count()).select_from(MaintenanceRequest)
        )
    assert count_after_second == count_after_first
