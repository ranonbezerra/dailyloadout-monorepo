"""Factory for the cache port."""

from __future__ import annotations

from dailyloadout.config import Settings

from .base import AbstractCache, NullCache


def get_cache(settings: Settings) -> AbstractCache:
    """Return a Redis cache in normal use, or a no-op cache under tests.

    Tests never open a real Redis connection; the no-op cache makes every
    read miss so behaviour is identical to "caching disabled".
    """
    if settings.app_env == "testing" or not settings.cache_enabled:
        return NullCache()

    from .redis_cache import RedisCache

    return RedisCache(settings.redis_url)
