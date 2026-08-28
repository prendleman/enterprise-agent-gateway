"""Unit tests for maintenance request idempotency."""

import pytest

from agent_gateway.auth.context import AuthContext, Role
from agent_gateway.config.settings import Settings, get_settings
from agent_gateway.storage.database import get_session_factory, init_db
from agent_gateway.storage.models import MaintenanceRequest
from agent_gateway.storage.seed import seed_database
from agent_gateway.tools.base import ToolContext
from agent_gateway.tools.create_maintenance_request import CreateMaintenanceRequestTool
from tests.conftest import PROJECT_ROOT


@pytest.fixture
async def tool_settings(tmp_path, monkeypatch):
    get_settings.cache_clear()
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{(tmp_path / 'tool.db').as_posix()}",
        demo_mode=True,
        datasets_dir=str(PROJECT_ROOT / "datasets"),
    )
    monkeypatch.setattr(
        "agent_gateway.config.settings.get_settings",
        lambda: settings,
    )
    await init_db(settings)
    await seed_database(settings, clear_existing=True)
    yield settings
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_duplicate_idempotency_key_returns_same_record(tool_settings) -> None:
    tool = CreateMaintenanceRequestTool()
    auth = AuthContext(
        subject="fm-northstar",
        tenant_id="northstar-facilities",
        role=Role.FACILITIES_MANAGER,
    )
    context = ToolContext(auth=auth, request_id="req-1")
    args = {
        "building_id": "bldg-001",
        "title": "Test request",
        "description": "Elevator inspection",
        "priority": "high",
        "idempotency_key": "unique-key-123",
    }
    first = await tool.execute(args, context)
    second = await tool.execute(args, context)
    assert first.status == "succeeded"
    assert second.status == "succeeded"
    assert first.data["request_id"] == second.data["request_id"]
    assert second.data["duplicate"] is True

    factory = get_session_factory(tool_settings)
    async with factory() as session:
        from sqlalchemy import func, select

        count = await session.scalar(select(func.count()).select_from(MaintenanceRequest))
        assert count == 1
