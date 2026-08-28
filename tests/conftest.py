"""Shared pytest fixtures for API and integration tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from agent_gateway.api.dependencies import override_dependencies, reset_cached_dependencies
from agent_gateway.config.settings import Settings, get_settings
from agent_gateway.main import create_app
from agent_gateway.storage.database import close_db

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Local-only demo API keys documented for portfolio use.
KEY_EMPLOYEE_NORTHSTAR = "demo-employee-northstar"
KEY_ANALYST_NORTHSTAR = "demo-analyst-northstar"
KEY_FM_NORTHSTAR = "demo-fm-northstar"
KEY_ANALYST_LAKESHORE = "demo-analyst-lakeshore"
KEY_ADMIN = "demo-admin"


@pytest.fixture
def test_settings(tmp_path, monkeypatch) -> Settings:
    db_path = tmp_path / "test.db"
    get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("USE_FAKE_PROVIDERS", "true")
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{db_path.as_posix()}",
        demo_mode=True,
        use_fake_providers=True,
        datasets_dir=str(PROJECT_ROOT / "datasets"),
        policies_path=str(PROJECT_ROOT / "config" / "policies.yaml"),
        tool_permissions_path=str(PROJECT_ROOT / "config" / "tool_permissions.yaml"),
        model_pricing_path=str(PROJECT_ROOT / "config" / "model_pricing.example.yaml"),
        artifacts_dir=str(tmp_path / "artifacts"),
    )
    get_settings.cache_clear()
    return settings


@pytest.fixture
async def seeded_app(test_settings: Settings, monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setattr(
        "agent_gateway.config.settings.get_settings",
        lambda: test_settings,
    )
    monkeypatch.setattr(
        "agent_gateway.api.dependencies.get_settings",
        lambda: test_settings,
    )
    reset_cached_dependencies()
    await close_db()
    app = create_app(test_settings)
    override_dependencies(app, test_settings)
    async with app.router.lifespan_context(app):
        yield app
    await close_db()
    get_settings.cache_clear()
    reset_cached_dependencies()


@pytest.fixture
async def client(seeded_app) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=seeded_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
