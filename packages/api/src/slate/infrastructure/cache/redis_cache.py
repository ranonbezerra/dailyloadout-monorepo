"""Redis-backed implementation of the cache port (ROADMAP Epic 17).

Best-effort: any Redis failure (down, timeout, serialization) is swallowed and
treated as a cache miss, so the caller always falls through to the live source.
"""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as redis
import structlog

from .base import AbstractCache

logger = structlog.get_logger()


class RedisCache(AbstractCache):
    def __init__(self, redis_url: str) -> None:
        self._redis: redis.Redis = redis.from_url(  # type: ignore[no-untyped-call]
            redis_url, decode_responses=True
        )

    async def get_json(self, key: str) -> Any | None:
        try:
            raw = await self._redis.get(key)
        except Exception:
            logger.warning("cache_get_failed", key=key, exc_info=True)
            return None
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return None

    async def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        try:
            await self._redis.set(key, json.dumps(value), ex=ttl_seconds)
        except Exception:
            logger.warning("cache_set_failed", key=key, exc_info=True)

    async def delete(self, key: str) -> None:
        try:
            await self._redis.delete(key)
        except Exception:
            logger.warning("cache_delete_failed", key=key, exc_info=True)

    async def delete_namespace(self, prefix: str) -> None:
        # SCAN (not KEYS) so a large keyspace never blocks Redis; the match is
        # scoped to *prefix* so the bust stays inside one namespace.
        try:
            async for key in self._redis.scan_iter(match=f"{prefix}*", count=500):
                await self._redis.delete(key)
        except Exception:
            logger.warning("cache_delete_namespace_failed", prefix=prefix, exc_info=True)
