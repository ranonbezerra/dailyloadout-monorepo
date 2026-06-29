"""Pydantic request / response schemas for the library layer."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from slate.config import settings
from slate.core.sanitization import (
    reject_control_chars,
    validate_cdn_url,
)

# Valid statuses for library entries.
LibraryStatus = Literal["backlog", "playing", "paused", "completed", "dropped"]

# Upper bounds on user-supplied game metadata. Titles/slugs flow unescaped into
# LLM prompts and the catalog, so they are capped and control-char-checked.
_MAX_TITLE_LEN = 200
_MAX_SLUG_LEN = 200
_MAX_SUMMARY_LEN = 5000
_MAX_GENRES = 30
_MAX_GENRE_LEN = 60
_MAX_COVER_URL_LEN = 500
_MAX_NOTES_LEN = 2000
# A game realistically lives on a handful of platforms; cap to bound fan-out.
_MAX_PLATFORM_IDS = 50


# ---------------------------------------------------------------------------
# Game schemas
# ---------------------------------------------------------------------------
class GameCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=_MAX_SLUG_LEN)
    title: str = Field(min_length=1, max_length=_MAX_TITLE_LEN)
    metadata_source: str = "manual"
    summary: str | None = Field(default=None, max_length=_MAX_SUMMARY_LEN)
    cover_url: str | None = Field(default=None, max_length=_MAX_COVER_URL_LEN)
    first_release_date: date | None = None
    genres: list[str] | None = Field(default=None, max_length=_MAX_GENRES)

    @field_validator("title", "slug")
    @classmethod
    def _no_control_chars(cls, value: str) -> str:
        """Reject control chars/newlines — the key prompt-injection mitigation."""
        return reject_control_chars(value, field="value")

    @field_validator("genres")
    @classmethod
    def _bound_genres(cls, value: list[str] | None) -> list[str] | None:
        """Cap per-genre length and reject control chars in each genre."""
        if value is None:
            return None
        cleaned: list[str] = []
        for genre in value:
            if len(genre) > _MAX_GENRE_LEN:
                raise ValueError(f"Each genre must be at most {_MAX_GENRE_LEN} characters.")
            cleaned.append(reject_control_chars(genre, field="genre"))
        return cleaned

    @field_validator("cover_url")
    @classmethod
    def _validate_cover_url(cls, value: str | None) -> str | None:
        """Null any cover URL that isn't https on the IGDB-CDN allowlist."""
        return validate_cdn_url(value, settings.igdb_cdn_allowed_hosts)


class GameResponse(BaseModel):
    public_id: UUID
    slug: str
    title: str
    igdb_id: int | None = None
    summary: str | None = None
    cover_url: str | None = None
    first_release_date: date | None = None
    genres: list[str] | None = None
    metadata_source: str
    created_at: datetime

    model_config = {"from_attributes": True}


class GameSearchResponse(BaseModel):
    items: list[GameResponse]
    total: int


# ---------------------------------------------------------------------------
# Platform schemas
# ---------------------------------------------------------------------------
class PlatformResponse(BaseModel):
    id: int
    slug: str
    label: str
    family: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Library entry schemas
# ---------------------------------------------------------------------------
class LibraryEntryCreate(BaseModel):
    game_public_id: UUID
    platform_ids: list[int] = Field(min_length=1, max_length=_MAX_PLATFORM_IDS)
    status: LibraryStatus = "backlog"
    notes: str | None = Field(default=None, max_length=_MAX_NOTES_LEN)
    acquired_at: date | None = None

    @field_validator("platform_ids")
    @classmethod
    def _dedupe_platform_ids(cls, value: list[int]) -> list[int]:
        """Drop duplicate platform ids while preserving first-seen order."""
        seen: set[int] = set()
        deduped: list[int] = []
        for platform_id in value:
            if platform_id not in seen:
                seen.add(platform_id)
                deduped.append(platform_id)
        return deduped


class LibraryEntryUpdate(BaseModel):
    status: LibraryStatus | None = None
    notes: str | None = Field(default=None, max_length=_MAX_NOTES_LEN)
    acquired_at: date | None = None


class LibraryEntryResponse(BaseModel):
    public_id: UUID
    game: GameResponse
    platform: PlatformResponse
    status: str
    acquired_at: date | None = None
    last_played_at: datetime | None = None
    play_session_next_action: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LibraryListResponse(BaseModel):
    items: list[LibraryEntryResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Grouped-by-game library schemas
# ---------------------------------------------------------------------------
class LibraryPlatformState(BaseModel):
    """A single per-platform play state for one game.

    ``public_id`` is the underlying :class:`LibraryEntry`'s public id, so the
    client can target this exact platform row for update / delete / play_session
    start while still seeing the game as one grouped item.
    """

    public_id: UUID
    platform: PlatformResponse
    status: str
    acquired_at: date | None = None
    last_played_at: datetime | None = None
    play_session_next_action: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LibraryGameGroup(BaseModel):
    """One game the user owns, with all of its per-platform states nested."""

    game: GameResponse
    platforms: list[LibraryPlatformState]


class LibraryGroupedResponse(BaseModel):
    """Grouped library list: one item per distinct game.

    ``total`` is the number of distinct GAMES (game-level pagination); ``limit``
    and ``offset`` page games, not per-platform entries.
    """

    items: list[LibraryGameGroup]
    total: int
    limit: int
    offset: int


__all__ = [
    "GameCreate",
    "GameResponse",
    "GameSearchResponse",
    "LibraryEntryCreate",
    "LibraryEntryResponse",
    "LibraryEntryUpdate",
    "LibraryGameGroup",
    "LibraryGroupedResponse",
    "LibraryListResponse",
    "LibraryPlatformState",
    "LibraryStatus",
    "PlatformResponse",
]
