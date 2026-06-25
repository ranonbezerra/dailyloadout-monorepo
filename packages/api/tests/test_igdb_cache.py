"""Unit tests for the IGDB result cache (ROADMAP Epic 17).

Exercises the caching business logic with a fake in-memory cache and a fake
inner client — no Redis, no HTTP.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from dailyloadout.infrastructure.cache.base import NullCache
from dailyloadout.infrastructure.igdb.cached import CachedIGDBClient, _cache_key
from dailyloadout.infrastructure.igdb.schemas import IGDBGame


class _FakeCache:
    """An in-memory AbstractCache for tests (ignores TTL)."""

    def __init__(self) -> None:
        self.store: dict[str, Any] = {}

    async def get_json(self, key: str) -> Any | None:
        return self.store.get(key)

    async def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        self.store[key] = value


class _FakeInner:
    """Records calls and returns canned games."""

    def __init__(self, games: list[IGDBGame]) -> None:
        self._games = games
        self.calls = 0

    async def search_games(self, query: str, limit: int = 5) -> list[IGDBGame]:
        self.calls += 1
        return self._games


_GAMES = [
    IGDBGame(
        igdb_id=14593,
        title="Hollow Knight",
        cover_url="https://img/co.jpg",
        summary="A metroidvania.",
        genres=["Platform", "Adventure"],
        first_release_date=date(2017, 2, 24),
    ),
    IGDBGame(igdb_id=2, title="No Cover Game"),  # all-None optional fields
]


def test_cache_key_is_normalized() -> None:
    assert _cache_key("  Hollow Knight ", 5) == "igdb:search:5:hollow knight"
    assert _cache_key("hollow knight", 3) != _cache_key("hollow knight", 5)


async def test_miss_calls_inner_and_stores() -> None:
    cache = _FakeCache()
    inner = _FakeInner(_GAMES)
    client = CachedIGDBClient(inner, cache, ttl_seconds=100)

    result = await client.search_games("Hollow Knight")

    assert inner.calls == 1
    assert [g.title for g in result] == ["Hollow Knight", "No Cover Game"]
    # The result was written to the cache.
    assert _cache_key("Hollow Knight", 5) in cache.store


async def test_hit_skips_inner_and_round_trips_fields() -> None:
    cache = _FakeCache()
    inner = _FakeInner(_GAMES)
    client = CachedIGDBClient(inner, cache, ttl_seconds=100)

    await client.search_games("Hollow Knight")  # populate
    again = await client.search_games("Hollow Knight")  # served from cache

    assert inner.calls == 1  # inner not called the second time
    game = again[0]
    assert game.igdb_id == 14593
    assert game.cover_url == "https://img/co.jpg"
    assert game.genres == ["Platform", "Adventure"]
    assert game.first_release_date == date(2017, 2, 24)
    # None optionals survive the round-trip.
    assert again[1].cover_url is None
    assert again[1].first_release_date is None


async def test_null_cache_always_misses() -> None:
    inner = _FakeInner(_GAMES)
    client = CachedIGDBClient(inner, NullCache(), ttl_seconds=100)

    await client.search_games("Hollow Knight")
    await client.search_games("Hollow Knight")

    # No caching → inner hit every time.
    assert inner.calls == 2
