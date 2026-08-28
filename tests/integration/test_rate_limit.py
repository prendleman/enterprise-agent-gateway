"""Rate limit enforcement on /v1/agents/run."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from tests.conftest import KEY_ANALYST_LAKESHORE, KEY_ANALYST_NORTHSTAR, PROJECT_ROOT

from agent_gateway.api.dependencies import override_dependencies, reset_cached_dependencies
from agent_gateway.config.settings import Settings, get_settings
from agent_gateway.main import create_app
from agent_gateway.storage.database import close_db


@pytest.fixture
async def limited_client(tmp_path, monkeypatch):
    db_path = tmp_path / "rate.db"
    get_settings.cache_clear()
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{db_path.as_posix()}",
        demo_mode=True,
        use_fake_providers=True,
        rate_limit_per_minute=2,
        datasets_dir=str(PROJECT_ROOT / "datasets"),
        policies_path=str(PROJECT_ROOT / "config" / "policies.yaml"),
        tool_permissions_path=str(PROJECT_ROOT / "config" / "tool_permissions.yaml"),
        model_pricing_path=str(PROJECT_ROOT / "config" / "model_pricing.example.yaml"),
        artifacts_dir=str(tmp_path / "artifacts"),
    )
    monkeypatch.setattr("agent_gateway.config.settings.get_settings", lambda: settings)
    monkeypatch.setattr("agent_gateway.api.dependencies.get_settings", lambda: settings)
    reset_cached_dependencies()
    await close_db()
    app = create_app(settings)
    override_dependencies(app, settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    await close_db()
    reset_cached_dependencies()


@pytest.mark.asyncio
async def test_requests_under_limit_succeed(limited_client: AsyncClient) -> None:
    response = await limited_client.post(
        "/v1/agents/run",
        headers={"X-API-Key": KEY_ANALYST_NORTHSTAR},
        json={"conversation_id": "rl-1", "query": "What is the safety policy?"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_requests_over_limit_return_429(limited_client: AsyncClient) -> None:
    payload = {"conversation_id": "rl-over", "query": "What is the safety policy?"}
    headers = {"X-API-Key": KEY_ANALYST_NORTHSTAR}
    assert (
        await limited_client.post("/v1/agents/run", headers=headers, json=payload)
    ).status_code == 200
    assert (
        await limited_client.post("/v1/agents/run", headers=headers, json=payload)
    ).status_code == 200
    blocked = await limited_client.post("/v1/agents/run", headers=headers, json=payload)
    assert blocked.status_code == 429
    assert blocked.headers["content-type"].startswith("application/problem+json")


@pytest.mark.asyncio
async def test_rate_limits_are_per_tenant(limited_client: AsyncClient) -> None:
    payload = {"conversation_id": "rl-tenant", "query": "What is the safety policy?"}
    for _ in range(2):
        response = await limited_client.post(
            "/v1/agents/run",
            headers={"X-API-Key": KEY_ANALYST_NORTHSTAR},
            json=payload,
        )
        assert response.status_code == 200
    other_tenant = await limited_client.post(
        "/v1/agents/run",
        headers={"X-API-Key": KEY_ANALYST_LAKESHORE},
        json=payload,
    )
    assert other_tenant.status_code == 200


@pytest.mark.asyncio
async def test_unauthenticated_requests_are_not_rate_limited_as_429(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/agents/run",
        json={"conversation_id": "no-auth", "query": "hello"},
    )
    assert response.status_code == 401
