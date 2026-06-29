"""Factory for the cache port."""

from __future__ import annotations

from slate.config import Settings

from .base import AbstractCache, NullCache

# Process-wide Redis cache: one connection pool shared across requests, rather
# than a fresh pool per dependency resolution. Tests never reach this path.
_redis_cache: AbstractCache | None = None


def get_cache(settings: Settings) -> AbstractCache:
    """Return a Redis cache in normal use, or a no-op cache under tests.

    Tests never open a real Redis connection; the no-op cache makes every
    read miss so behaviour is identical to "caching disabled". The Redis cache
    is memoised so all callers share one connection pool.
    """
    if settings.app_env == "testing" or not settings.cache_enabled:
        return NullCache()

    global _redis_cache
    if _redis_cache is None:
        from .redis_cache import RedisCache

        _redis_cache = RedisCache(settings.redis_url)
    return _redis_cache
