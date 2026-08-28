"""Building summary lookup tool."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select

from agent_gateway.storage.database import get_session_factory
from agent_gateway.storage.models import Building, WorkOrder
from agent_gateway.tools.base import Tool, ToolContext, ToolResult


class GetBuildingSummaryTool(Tool):
    """Return aggregate building information for the caller tenant."""

    name = "get_building_summary"

    def validate_arguments(self, arguments: dict[str, Any]) -> dict[str, Any]:
        building_id = arguments.get("building_id")
        building_name = arguments.get("building_name")
        if not building_id and not building_name:
            msg = "building_id or building_name is required"
            raise ValueError(msg)
        return {
            "building_id": str(building_id).strip() if building_id else None,
            "building_name": str(building_name).strip() if building_name else None,
        }

    async def execute(self, arguments: dict[str, Any], context: ToolContext) -> ToolResult:
        args = self.validate_arguments(arguments)
        factory = get_session_factory()
        async with factory() as session:
            stmt = select(Building).where(Building.tenant_id == context.auth.tenant_id)
            if args["building_id"]:
                stmt = stmt.where(Building.id == args["building_id"])
            elif args["building_name"]:
                stmt = stmt.where(func.lower(Building.name) == args["building_name"].lower())

            building = (await session.execute(stmt)).scalar_one_or_none()
            if building is None:
                return ToolResult(
                    name=self.name,
                    status="failed",
                    error="Building not found for tenant",
                )

            counts = await session.execute(
                select(WorkOrder.status, func.count())
                .where(
                    WorkOrder.tenant_id == context.auth.tenant_id,
                    WorkOrder.building_id == building.id,
                )
                .group_by(WorkOrder.status)
            )
            status_counts = {status: count for status, count in counts.all()}
            data = {
                "building_id": building.id,
                "name": building.name,
                "address": building.address,
                "city": building.city,
                "property_type": building.property_type,
                "square_feet": building.square_feet,
                "work_order_status_counts": status_counts,
            }
            return ToolResult(
                name=self.name,
                status="succeeded",
                data=data,
                citations=[{"source_id": building.id, "title": building.name}],
            )
