"""Simple per-tenant token-bucket rate limiter."""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class _Bucket:
    tokens: float
    updated_at: float


class RateLimiter:
    """In-memory rate limiter keyed by tenant."""

    def __init__(self, *, limit_per_minute: int = 120) -> None:
        self._limit_per_minute = limit_per_minute
        self._buckets: dict[str, _Bucket] = {}

    async def acquire(self, *, key: str) -> bool:
        now = time.monotonic()
        refill_rate = self._limit_per_minute / 60.0
        bucket = self._buckets.get(key)
        if bucket is None:
            self._buckets[key] = _Bucket(tokens=self._limit_per_minute - 1, updated_at=now)
            return True

        elapsed = now - bucket.updated_at
        bucket.tokens = min(self._limit_per_minute, bucket.tokens + elapsed * refill_rate)
        bucket.updated_at = now
        if bucket.tokens < 1:
            return False
        bucket.tokens -= 1
        return True
