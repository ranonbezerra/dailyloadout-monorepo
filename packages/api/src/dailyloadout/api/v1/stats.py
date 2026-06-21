"""Stats API endpoints."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

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


@router.get("/overview", response_model=StatsOverviewResponse)
async def stats_overview(
    current_user: CurrentUserDep,
    stats_service: StatsServiceDep,
) -> StatsOverviewResponse:
    return await stats_service.get_overview(current_user.id, current_user.created_at)


@router.get("/play-heatmap", response_model=PlayHeatmapResponse)
async def play_heatmap(
    current_user: CurrentUserDep,
    stats_service: StatsServiceDep,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
) -> PlayHeatmapResponse:
    return await stats_service.get_play_heatmap(current_user.id, from_date, to_date)


@router.get("/genres", response_model=GenreStatsResponse)
async def genre_stats(
    current_user: CurrentUserDep,
    stats_service: StatsServiceDep,
) -> GenreStatsResponse:
    return await stats_service.get_genre_stats(current_user.id)


@router.get("/platforms", response_model=PlatformStatsResponse)
async def platform_stats(
    current_user: CurrentUserDep,
    stats_service: StatsServiceDep,
) -> PlatformStatsResponse:
    return await stats_service.get_platform_stats(current_user.id)


@router.get("/timeline", response_model=TimelineResponse)
async def mission_timeline(
    current_user: CurrentUserDep,
    stats_service: StatsServiceDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> TimelineResponse:
    return await stats_service.get_timeline(current_user.id, limit=limit, offset=offset)
