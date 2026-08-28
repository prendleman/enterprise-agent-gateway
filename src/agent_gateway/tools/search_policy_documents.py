"""Search policy documents via FTS retrieval."""

from __future__ import annotations

from typing import Any

from agent_gateway.retrieval.base import RetrievalQuery
from agent_gateway.retrieval.sqlite_fts import SqliteFtsRetriever
from agent_gateway.tools.base import Tool, ToolContext, ToolResult


class SearchPolicyDocumentsTool(Tool):
    """Retrieve tenant-scoped policy documents."""

    name = "search_policy_documents"

    def __init__(self, retriever: SqliteFtsRetriever | None = None) -> None:
        self._retriever = retriever or SqliteFtsRetriever()

    def validate_arguments(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = str(arguments.get("query", "")).strip()
        if not query:
            msg = "query is required"
            raise ValueError(msg)
        limit = int(arguments.get("limit", 5))
        return {"query": query, "limit": max(1, min(limit, 20))}

    async def execute(self, arguments: dict[str, Any], context: ToolContext) -> ToolResult:
        args = self.validate_arguments(arguments)
        results = await self._retriever.search(
            RetrievalQuery(
                query=args["query"],
                tenant_id=context.auth.tenant_id,
                source_type="policy_documents",
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
