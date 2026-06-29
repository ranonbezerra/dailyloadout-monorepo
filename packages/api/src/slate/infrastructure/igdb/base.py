"""Structural contract for IGDB search, so the live client and the caching
decorator are interchangeable (ROADMAP Epic 17)."""

from __future__ import annotations

from typing import Protocol

from .schemas import IGDBGame


class IGDBSearchClient(Protocol):
    """Anything that can search IGDB for games (live client, cached wrapper)."""

    async def search_games(self, query: str, limit: int = 5) -> list[IGDBGame]: ...
