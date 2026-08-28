"""Search work orders via FTS retrieval."""

from __future__ import annotations

from typing import Any

from agent_gateway.retrieval.base import RetrievalQuery
from agent_gateway.retrieval.sqlite_fts import SqliteFtsRetriever
from agent_gateway.tools.base import Tool, ToolContext, ToolResult


class SearchWorkOrdersTool(Tool):
    """Retrieve tenant-scoped work orders."""

    name = "search_work_orders"

    def __init__(self, retriever: SqliteFtsRetriever | None = None) -> None:
        self._retriever = retriever or SqliteFtsRetriever()

    def validate_arguments(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = str(arguments.get("query", "")).strip()
        if not query:
            msg = "query is required"
            raise ValueError(msg)
        limit = int(arguments.get("limit", 5))
        normalized: dict[str, Any] = {"query": query, "limit": max(1, min(limit, 20))}
        if building_name := arguments.get("building_name"):
            normalized["building_name"] = str(building_name).strip()
        if status := arguments.get("status"):
            normalized["status"] = str(status).strip()
        return normalized

    async def execute(self, arguments: dict[str, Any], context: ToolContext) -> ToolResult:
        args = self.validate_arguments(arguments)
        query = args["query"]
        if building_name := args.get("building_name"):
            query = f"{query} {building_name}"
        if status := args.get("status"):
            query = f"{query} {status}"

        results = await self._retriever.search(
            RetrievalQuery(
                query=query,
                tenant_id=context.auth.tenant_id,
                source_type="work_orders",
                limit=args["limit"],
            )
        )
        citations = [{"source_id": r.source_id, "title": r.title} for r in results]
        return ToolResult(
            name=self.name,
            status="succeeded",
            data={"results": [r.model_dump() for r in results], "count": len(results)},
            citations=citations,
        )
