"""Create maintenance request write tool with idempotency."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select

from agent_gateway.storage.database import get_session_factory
from agent_gateway.storage.models import Building, MaintenanceRequest
from agent_gateway.tools.base import Tool, ToolContext, ToolResult


class CreateMaintenanceRequestTool(Tool):
    """Create a tenant-scoped maintenance request."""

    name = "create_maintenance_request"

    def validate_arguments(self, arguments: dict[str, Any]) -> dict[str, Any]:
        required = ("building_id", "title", "description", "priority", "idempotency_key")
        missing = [field for field in required if not arguments.get(field)]
        if missing:
            msg = f"Missing required fields: {', '.join(missing)}"
            raise ValueError(msg)
        priority = str(arguments["priority"]).lower()
        if priority not in {"low", "medium", "high", "critical"}:
            msg = "priority must be one of low, medium, high, critical"
            raise ValueError(msg)
        return {
            "building_id": str(arguments["building_id"]).strip(),
            "title": str(arguments["title"]).strip(),
            "description": str(arguments["description"]).strip(),
            "priority": priority,
            "idempotency_key": str(arguments["idempotency_key"]).strip(),
        }

    async def execute(self, arguments: dict[str, Any], context: ToolContext) -> ToolResult:
        args = self.validate_arguments(arguments)
        factory = get_session_factory()
        async with factory() as session:
            existing = await session.execute(
                select(MaintenanceRequest).where(
                    MaintenanceRequest.tenant_id == context.auth.tenant_id,
                    MaintenanceRequest.idempotency_key == args["idempotency_key"],
                )
            )
            found = existing.scalar_one_or_none()
            if found is not None:
                return ToolResult(
                    name=self.name,
                    status="succeeded",
                    data={
                        "request_id": found.id,
                        "duplicate": True,
                        "building_id": found.building_id,
                        "title": found.title,
                    },
                    citations=[{"source_id": found.id, "title": found.title}],
                )

            building = await session.execute(
                select(Building).where(
                    Building.id == args["building_id"],
                    Building.tenant_id == context.auth.tenant_id,
                )
            )
            if building.scalar_one_or_none() is None:
                return ToolResult(
                    name=self.name,
                    status="failed",
                    error="Building not found for tenant",
                )

            request_id = f"mreq-{uuid.uuid4().hex[:12]}"
            record = MaintenanceRequest(
                id=request_id,
                tenant_id=context.auth.tenant_id,
                building_id=args["building_id"],
                title=args["title"],
                description=args["description"],
                priority=args["priority"],
                idempotency_key=args["idempotency_key"],
                created_by=context.auth.subject,
            )
            session.add(record)
            await session.commit()
            return ToolResult(
                name=self.name,
                status="succeeded",
                data={
                    "request_id": request_id,
                    "duplicate": False,
                    "building_id": args["building_id"],
                    "title": args["title"],
                },
                citations=[{"source_id": request_id, "title": args["title"]}],
            )
