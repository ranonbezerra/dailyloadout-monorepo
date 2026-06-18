"""Dataclasses for IGDB API response data."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class IGDBGame:
    """Structured representation of a game from the IGDB API."""

    igdb_id: int
    title: str
    cover_url: str | None = None
    summary: str | None = None
    genres: list[str] | None = None
    first_release_date: date | None = None


@dataclass
class IGDBSearchResult:
    """A batch of search results from IGDB."""

    games: list[IGDBGame] = field(default_factory=list)
