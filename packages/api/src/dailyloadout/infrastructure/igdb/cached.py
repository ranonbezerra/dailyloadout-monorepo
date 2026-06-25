"""Caching decorator for IGDB search (ROADMAP Epic 17).

Wraps any ``IGDBSearchClient`` with a best-effort cache. Game metadata is stable,
so identical searches (very common on bulk library import) are served from the
cache instead of re-hitting the rate-limited IGDB API. A cache miss/outage falls
through to the live client transparently.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import structlog

from dailyloadout.infrastructure.cache.base import AbstractCache

from .base import IGDBSearchClient
from .schemas import IGDBGame

logger = structlog.get_logger()

_KEY_PREFIX = "igdb:search"


def _cache_key(query: str, limit: int) -> str:
    return f"{_KEY_PREFIX}:{limit}:{query.strip().lower()}"


def _to_dict(game: IGDBGame) -> dict[str, Any]:
    return {
        "igdb_id": game.igdb_id,
        "title": game.title,
        "cover_url": game.cover_url,
        "summary": game.summary,
        "genres": game.genres,
        "first_release_date": (
            game.first_release_date.isoformat() if game.first_release_date else None
        ),
    }


def _from_dict(data: dict[str, Any]) -> IGDBGame:
    raw_date = data.get("first_release_date")
    return IGDBGame(
        igdb_id=int(data["igdb_id"]),
        title=str(data["title"]),
        cover_url=data.get("cover_url"),
        summary=data.get("summary"),
        genres=data.get("genres"),
        first_release_date=date.fromisoformat(raw_date) if raw_date else None,
    )


class CachedIGDBClient:
    """An ``IGDBSearchClient`` that caches results around an inner client."""

    def __init__(self, inner: IGDBSearchClient, cache: AbstractCache, ttl_seconds: int) -> None:
        self._inner = inner
        self._cache = cache
        self._ttl = ttl_seconds

    async def search_games(self, query: str, limit: int = 5) -> list[IGDBGame]:
        key = _cache_key(query, limit)

        cached = await self._cache.get_json(key)
        if isinstance(cached, list):
            return [_from_dict(item) for item in cached]

        games = await self._inner.search_games(query, limit)
        await self._cache.set_json(key, [_to_dict(g) for g in games], self._ttl)
        return games
