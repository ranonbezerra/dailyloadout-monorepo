"""Cache factory + NullCache tests (ROADMAP Epic 18).

Covers provider selection and memoisation. Constructing a ``RedisCache`` is
connectionless (``redis.from_url`` is lazy), so no live Redis is needed.
"""

from __future__ import annotations

from dailyloadout.config import Settings
from dailyloadout.infrastructure.cache import factory
from dailyloadout.infrastructure.cache.base import NullCache


def test_testing_env_returns_null_cache() -> None:
    cache = factory.get_cache(Settings(app_env="testing", cache_enabled=True))
    assert isinstance(cache, NullCache)


def test_disabled_returns_null_cache() -> None:
    cache = factory.get_cache(Settings(app_env="production", cache_enabled=False))
    assert isinstance(cache, NullCache)


def test_enabled_returns_memoized_redis_cache() -> None:
    from dailyloadout.infrastructure.cache.redis_cache import RedisCache

    factory._redis_cache = None  # reset the process singleton for the test
    try:
        settings = Settings(
            app_env="production",
            cache_enabled=True,
            redis_url="redis://localhost:6379/0",
        )
        first = factory.get_cache(settings)
        second = factory.get_cache(settings)
        assert isinstance(first, RedisCache)
        assert first is second  # memoised: one shared instance
    finally:
        factory._redis_cache = None


async def test_null_cache_methods_are_noops() -> None:
    cache = NullCache()
    assert await cache.get_json("k") is None
    assert await cache.set_json("k", 1, 10) is None
    assert await cache.delete("k") is None
    assert await cache.delete_namespace("p:") is None
