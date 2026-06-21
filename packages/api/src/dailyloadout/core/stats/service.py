"""Stats service: aggregate read-only analytics."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any

from dailyloadout.core.stats.schemas import (
    GenreStat,
    GenreStatsResponse,
    HeatmapDay,
    PlatformStat,
    PlatformStatsResponse,
    PlayHeatmapResponse,
    StatsOverviewResponse,
    TimelineEntry,
    TimelineResponse,
)
from dailyloadout.infrastructure.db.repositories.stats import StatsRepository


class StatsService:
    def __init__(self, stats_repo: StatsRepository) -> None:
        self._repo = stats_repo

    async def get_overview(self, user_id: int, user_created_at: datetime) -> StatsOverviewResponse:
        total_games = await self._repo.total_games(user_id)
        status_counts = await self._repo.status_counts(user_id)
        missions_30d = await self._repo.missions_last_30d(user_id)
        avg_duration = await self._repo.avg_mission_duration_minutes(user_id)
        return StatsOverviewResponse(
            total_games=total_games,
            status_counts=status_counts,
            missions_last_30d=missions_30d,
            avg_mission_duration_minutes=avg_duration,
            user_created_at=user_created_at,
        )

    async def get_play_heatmap(
        self, user_id: int, from_date: date | None, to_date: date | None
    ) -> PlayHeatmapResponse:
        missions = await self._repo.ended_missions_in_range(user_id, from_date, to_date)
        # Group by date, compute durations in Python
        day_map: dict[date, dict[str, int]] = defaultdict(lambda: {"count": 0, "total_minutes": 0})
        for m in missions:
            day = m.started_at.date()
            duration = int((m.ended_at - m.started_at).total_seconds() / 60) if m.ended_at else 0
            day_map[day]["count"] += 1
            day_map[day]["total_minutes"] += duration

        days = [
            HeatmapDay(date=d, count=v["count"], total_minutes=v["total_minutes"])
            for d, v in sorted(day_map.items())
        ]
        return PlayHeatmapResponse(days=days)

    async def get_genre_stats(self, user_id: int) -> GenreStatsResponse:
        missions = await self._repo.ended_missions_with_games(user_id)
        genre_map: dict[str, dict[str, int]] = defaultdict(
            lambda: {"total_minutes": 0, "mission_count": 0}
        )
        for m in missions:
            duration = int((m.ended_at - m.started_at).total_seconds() / 60) if m.ended_at else 0
            game_genres = m.library_entry.game.genres or []
            for genre in game_genres:
                genre_map[genre]["total_minutes"] += duration
                genre_map[genre]["mission_count"] += 1

        genre_stats = sorted(
            [
                GenreStat(
                    genre=g,
                    total_minutes=v["total_minutes"],
                    mission_count=v["mission_count"],
                )
                for g, v in genre_map.items()
            ],
            key=lambda x: x.total_minutes,
            reverse=True,
        )
        return GenreStatsResponse(genres=genre_stats)

    async def get_platform_stats(self, user_id: int) -> PlatformStatsResponse:
        entries, missions = await self._repo.library_and_missions_for_platforms(user_id)
        # Build platform map from library entries
        plat_map: dict[int, dict[str, Any]] = {}
        for entry in entries:
            pid = entry.platform_id
            if pid not in plat_map:
                plat_map[pid] = {
                    "platform_slug": entry.platform.slug,
                    "platform_label": entry.platform.label,
                    "game_count": 0,
                    "mission_count": 0,
                    "total_minutes": 0,
                }
            plat_map[pid]["game_count"] += 1

        # Count missions per platform
        for m in missions:
            pid = m.library_entry.platform_id
            if pid in plat_map:
                plat_map[pid]["mission_count"] += 1
                if m.ended_at:
                    plat_map[pid]["total_minutes"] += int(
                        (m.ended_at - m.started_at).total_seconds() / 60
                    )

        platforms = sorted(
            [PlatformStat(**v) for v in plat_map.values()],
            key=lambda x: x.mission_count,
            reverse=True,
        )
        return PlatformStatsResponse(platforms=platforms)

    async def get_timeline(
        self, user_id: int, limit: int = 20, offset: int = 0
    ) -> TimelineResponse:
        missions, total = await self._repo.recent_missions(user_id, limit=limit, offset=offset)
        items = []
        for m in missions:
            duration = None
            if m.ended_at and m.started_at:
                duration = int((m.ended_at - m.started_at).total_seconds() / 60)
            items.append(
                TimelineEntry(
                    public_id=m.public_id,
                    game_title=m.library_entry.game.title,
                    platform_label=m.library_entry.platform.label,
                    mission_type=m.mission_type,
                    briefing_text=m.briefing_text,
                    debrief_text=m.debrief_text,
                    ended_via=m.ended_via,
                    started_at=m.started_at,
                    ended_at=m.ended_at,
                    duration_minutes=duration,
                )
            )
        return TimelineResponse(items=items, total=total)
