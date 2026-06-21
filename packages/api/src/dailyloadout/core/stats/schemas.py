"""Pydantic request / response schemas for the stats layer."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class StatsOverviewResponse(BaseModel):
    total_games: int
    status_counts: dict[str, int]
    missions_last_30d: int
    avg_mission_duration_minutes: float | None
    user_created_at: datetime


class HeatmapDay(BaseModel):
    date: date
    count: int
    total_minutes: int


class PlayHeatmapResponse(BaseModel):
    days: list[HeatmapDay]


class GenreStat(BaseModel):
    genre: str
    total_minutes: int
    mission_count: int


class GenreStatsResponse(BaseModel):
    genres: list[GenreStat]


class PlatformStat(BaseModel):
    platform_slug: str
    platform_label: str
    game_count: int
    mission_count: int
    total_minutes: int


class PlatformStatsResponse(BaseModel):
    platforms: list[PlatformStat]


class TimelineEntry(BaseModel):
    public_id: UUID
    game_title: str
    platform_label: str
    mission_type: str
    briefing_text: str | None = None
    debrief_text: str | None = None
    ended_via: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    duration_minutes: int | None = None


class TimelineResponse(BaseModel):
    items: list[TimelineEntry]
    total: int
