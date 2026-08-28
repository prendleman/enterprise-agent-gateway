"""Unit tests for health endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from agent_gateway.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.mark.asyncio
async def test_health_live_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_ready_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] is True
    assert body["demo_mode"] is True


@pytest.mark.asyncio
async def test_request_id_header_propagated(client: AsyncClient) -> None:
    custom_id = "test-request-id-12345"
    response = await client.get("/health/live", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id
