"""In-memory idempotency helpers for write tools."""

from __future__ import annotations

from typing import Any


class IdempotencyStore:
    """Process-local idempotency cache (database is source of truth for writes)."""

    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}

    async def get(self, key: str) -> Any | None:
        return self._cache.get(key)

    async def set(self, key: str, value: Any) -> None:
        self._cache[key] = value
