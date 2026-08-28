"""Tool registry."""

from __future__ import annotations

from agent_gateway.tools.base import Tool
from agent_gateway.tools.building_summary import GetBuildingSummaryTool
from agent_gateway.tools.create_maintenance_request import CreateMaintenanceRequestTool
from agent_gateway.tools.search_policy_documents import SearchPolicyDocumentsTool
from agent_gateway.tools.search_work_orders import SearchWorkOrdersTool


class ToolRegistry:
    """Registry of executable agent tools."""

    def __init__(self, tools: dict[str, Tool] | None = None) -> None:
        default_tools: list[Tool] = [
            SearchPolicyDocumentsTool(),
            SearchWorkOrdersTool(),
            GetBuildingSummaryTool(),
            CreateMaintenanceRequestTool(),
        ]
        self._tools = tools or {tool.name: tool for tool in default_tools}

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return list(self._tools.keys())
