"""Process-wide shared ``redis.asyncio`` client.

A single connection pool is reused across requests (rate limiting, etc.) rather
than opening a fresh pool per dependency resolution. Mirrors the memoisation in
``cache/factory.py`` but exposes the raw client so callers can run arbitrary
commands (``INCR``/``EXPIRE`` for the rate limiter).
"""

from __future__ import annotations

import redis.asyncio as redis

from dailyloadout.config import settings

_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    """Return the process-wide async Redis client (memoised connection pool)."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(  # type: ignore[no-untyped-call]
            settings.redis_url, decode_responses=True
        )
    return _redis_client
