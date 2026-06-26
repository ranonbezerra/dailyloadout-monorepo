"""Stats API endpoints."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from dailyloadout.api.v1._rate_limit import rate_limit
from dailyloadout.config import settings
from dailyloadout.core.stats.schemas import (
    GenreStatsResponse,
    PlatformStatsResponse,
    PlayHeatmapResponse,
    StatsOverviewResponse,
    TimelineResponse,
)
from dailyloadout.deps import CurrentUserDep
from dailyloadout.deps.stats import StatsServiceDep

router = APIRouter(prefix="/v1/stats", tags=["stats"])

# Generous per-user limiter on the read-only analytics endpoints (anti-scraping
# backstop, not a cost control). Shared across every stats route.
_stats_rate_limit = Depends(
    rate_limit("stats_read", settings.rate_limit_read_per_minute, 60, by="user")
)


@router.get("/overview", response_model=StatsOverviewResponse, dependencies=[_stats_rate_limit])
async def stats_overview(
    current_user: CurrentUserDep,
    stats_service: StatsServiceDep,
) -> StatsOverviewResponse:
    return await stats_service.get_overview(current_user.id, current_user.created_at)


@router.get("/play-heatmap", response_model=PlayHeatmapResponse, dependencies=[_stats_rate_limit])
async def play_heatmap(
    current_user: CurrentUserDep,
    stats_service: StatsServiceDep,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
) -> PlayHeatmapResponse:
    return await stats_service.get_play_heatmap(current_user.id, from_date, to_date)


@router.get("/genres", response_model=GenreStatsResponse, dependencies=[_stats_rate_limit])
async def genre_stats(
    current_user: CurrentUserDep,
    stats_service: StatsServiceDep,
) -> GenreStatsResponse:
    return await stats_service.get_genre_stats(current_user.id)


@router.get("/platforms", response_model=PlatformStatsResponse, dependencies=[_stats_rate_limit])
async def platform_stats(
    current_user: CurrentUserDep,
    stats_service: StatsServiceDep,
) -> PlatformStatsResponse:
    return await stats_service.get_platform_stats(current_user.id)


@router.get("/timeline", response_model=TimelineResponse, dependencies=[_stats_rate_limit])
async def mission_timeline(
    current_user: CurrentUserDep,
    stats_service: StatsServiceDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> TimelineResponse:
    return await stats_service.get_timeline(current_user.id, limit=limit, offset=offset)
