"""Load synthetic datasets into the database."""

import json
from pathlib import Path

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from agent_gateway.config.settings import Settings, get_settings
from agent_gateway.storage.database import init_db
from agent_gateway.storage.models import Building, PolicyDocument, WorkOrder

logger = structlog.get_logger(__name__)

TENANT_NORTHSTAR = "northstar-facilities"
TENANT_LAKESHORE = "lakeshore-properties"


def _tenant_for_building(building_id: str) -> str:
    """Assign demo tenants by building id suffix."""
    suffix = int(building_id.rsplit("-", maxsplit=1)[-1])
    return TENANT_NORTHSTAR if suffix <= 5 else TENANT_LAKESHORE


def _load_json(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        msg = f"Expected JSON array in {path}"
        raise ValueError(msg)
    return data


async def seed_from_datasets(
    session: AsyncSession,
    settings: Settings | None = None,
    *,
    clear_existing: bool = False,
) -> dict[str, int]:
    """Seed buildings, work orders, and policy documents from JSON datasets."""
    cfg = settings or get_settings()
    datasets_dir = Path(cfg.datasets_dir)

    if clear_existing:
        from sqlalchemy import delete

        from agent_gateway.storage.models import MaintenanceRequest

        await session.execute(delete(MaintenanceRequest))
        await session.execute(delete(WorkOrder))
        await session.execute(delete(PolicyDocument))
        await session.execute(delete(Building))
        await session.commit()

    counts = {"buildings": 0, "work_orders": 0, "policy_documents": 0}
    building_tenants: dict[str, str] = {}

    buildings_path = datasets_dir / "buildings.json"
    if buildings_path.exists():
        for row in _load_json(buildings_path):
            tenant_id = _tenant_for_building(row["id"])
            building_tenants[row["id"]] = tenant_id
            if row["id"] == "bldg-010":
                row = {**row, "name": "Lakeshore Tower"}
            session.add(Building(**row, tenant_id=tenant_id))
            counts["buildings"] += 1

    work_orders_path = datasets_dir / "work_orders.json"
    if work_orders_path.exists():
        for row in _load_json(work_orders_path):
            tenant_id = building_tenants.get(row["building_id"], TENANT_NORTHSTAR)
            session.add(WorkOrder(**row, tenant_id=tenant_id))
            counts["work_orders"] += 1

    policies_path = datasets_dir / "policy_documents.json"
    if policies_path.exists():
        for index, row in enumerate(_load_json(policies_path)):
            tenant_id = TENANT_NORTHSTAR if index % 2 == 0 else TENANT_LAKESHORE
            session.add(PolicyDocument(**row, tenant_id=tenant_id))
            counts["policy_documents"] += 1

    await session.commit()
    logger.info("seed_complete", **counts)
    return counts


async def seed_database(
    settings: Settings | None = None, *, clear_existing: bool = True
) -> dict[str, int]:
    """Initialize schema and load synthetic datasets."""
    cfg = settings or get_settings()
    await init_db(cfg)

    from agent_gateway.storage.database import get_session_factory

    factory = get_session_factory(cfg)
    async with factory() as session:
        counts = await seed_from_datasets(session, cfg, clear_existing=clear_existing)
    await _rebuild_fts(cfg)
    return counts


async def _rebuild_fts(settings: Settings) -> None:
    """Rebuild FTS5 indexes after seeding."""
    from agent_gateway.retrieval.sqlite_fts import SqliteFtsRetriever

    retriever = SqliteFtsRetriever(settings)
    await retriever.rebuild_indexes()
