"""Pydantic request / response schemas for the library layer."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

# Valid statuses for library entries.
LibraryStatus = Literal["backlog", "playing", "paused", "completed", "dropped"]


# ---------------------------------------------------------------------------
# Game schemas
# ---------------------------------------------------------------------------
class GameCreate(BaseModel):
    slug: str = Field(min_length=1)
    title: str = Field(min_length=1)
    metadata_source: str = "manual"
    summary: str | None = None
    cover_url: str | None = None
    first_release_date: date | None = None
    genres: list[str] | None = None


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
    platform_id: int
    status: LibraryStatus = "backlog"
    notes: str | None = None
    acquired_at: date | None = None


class LibraryEntryUpdate(BaseModel):
    status: LibraryStatus | None = None
    notes: str | None = None
    acquired_at: date | None = None


class LibraryEntryResponse(BaseModel):
    public_id: UUID
    game: GameResponse
    platform: PlatformResponse
    status: str
    acquired_at: date | None = None
    last_played_at: datetime | None = None
    mission_next_action: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LibraryListResponse(BaseModel):
    items: list[LibraryEntryResponse]
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
    "LibraryListResponse",
    "LibraryStatus",
    "PlatformResponse",
]
