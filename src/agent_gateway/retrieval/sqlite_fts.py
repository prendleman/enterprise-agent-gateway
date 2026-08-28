"""SQLite FTS5 retrieval implementation."""

from __future__ import annotations

import re

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from agent_gateway.config.settings import Settings, get_settings
from agent_gateway.retrieval.base import RetrievalQuery, RetrievalResult
from agent_gateway.storage.database import get_session_factory

logger = structlog.get_logger(__name__)

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def normalize_query(query: str) -> str:
    """Normalize user query for stable FTS matching."""
    tokens = _TOKEN_RE.findall(query.lower())
    stopwords = {"what", "the", "a", "an", "for", "to", "at", "is", "are", "our", "your", "apply"}
    keywords = [t for t in tokens if t not in stopwords and len(t) > 2]
    if not keywords:
        keywords = tokens
    return " OR ".join(keywords[:8])


class SqliteFtsRetriever:
    """Deterministic FTS5 retriever backed by seeded SQLite tables."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def rebuild_indexes(self) -> None:
        factory = get_session_factory(self._settings)
        async with factory() as session:
            await self._ensure_schema(session)
            await session.execute(text("DELETE FROM policy_documents_fts"))
            await session.execute(text("DELETE FROM work_orders_fts"))
            await session.execute(
                text(
                    """
                    INSERT INTO policy_documents_fts(rowid, source_id, tenant_id, title, body)
                    SELECT rowid, id, tenant_id, title, title || ' ' || summary || ' ' || content
                    FROM policy_documents
                    """
                )
            )
            await session.execute(
                text(
                    """
                    INSERT INTO work_orders_fts(rowid, source_id, tenant_id, title, body)
                    SELECT rowid, id, tenant_id, title,
                           title || ' ' || description || ' ' || category
                    FROM work_orders
                    """
                )
            )
            await session.commit()
            logger.info("fts_indexes_rebuilt")

    async def search(self, request: RetrievalQuery) -> list[RetrievalResult]:
        normalized = normalize_query(request.query)
        if not normalized:
            return []

        table = self._table_for_source(request.source_type)
        if table is None:
            return []

        factory = get_session_factory(self._settings)
        async with factory() as session:
            await self._ensure_schema(session)
            rows = await session.execute(
                text(
                    f"""
                    SELECT source_id, title, body, bm25({table}) AS score
                    FROM {table}
                    WHERE tenant_id = :tenant_id
                      AND {table} MATCH :query
                    ORDER BY score
                    LIMIT :limit
                    """
                ),
                {
                    "tenant_id": request.tenant_id,
                    "query": normalized,
                    "limit": request.limit,
                },
            )
            results: list[RetrievalResult] = []
            for row in rows:
                excerpt = str(row.body)[:240]
                results.append(
                    RetrievalResult(
                        source_id=str(row.source_id),
                        title=str(row.title),
                        excerpt=excerpt,
                        score=abs(float(row.score)),
                        source_type=request.source_type or "document",
                    )
                )
            return results

    @staticmethod
    def _table_for_source(source_type: str | None) -> str | None:
        if source_type in (None, "policy", "policy_documents"):
            return "policy_documents_fts"
        if source_type in ("work_order", "work_orders"):
            return "work_orders_fts"
        return None

    async def _ensure_schema(self, session: AsyncSession) -> None:
        await session.execute(
            text(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS policy_documents_fts USING fts5(
                    source_id UNINDEXED,
                    tenant_id UNINDEXED,
                    title,
                    body,
                    tokenize='porter'
                )
                """
            )
        )
        await session.execute(
            text(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS work_orders_fts USING fts5(
                    source_id UNINDEXED,
                    tenant_id UNINDEXED,
                    title,
                    body,
                    tokenize='porter'
                )
                """
            )
        )
