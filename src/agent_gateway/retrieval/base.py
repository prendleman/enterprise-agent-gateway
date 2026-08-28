"""Retrieval protocol and result models."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field


class RetrievalResult(BaseModel):
    """Single retrieved document excerpt."""

    source_id: str
    title: str
    excerpt: str
    score: float = Field(ge=0.0)
    source_type: str = "document"


class RetrievalQuery(BaseModel):
    """Normalized retrieval request."""

    query: str
    tenant_id: str
    source_type: str | None = None
    limit: int = Field(default=5, ge=1, le=20)


@runtime_checkable
class Retriever(Protocol):
    """Protocol for search backends used by tools and the agent."""

    async def search(self, request: RetrievalQuery) -> list[RetrievalResult]:
        """Return ranked retrieval results scoped to tenant."""

    async def rebuild_indexes(self) -> None:
        """Rebuild search indexes from source tables."""
