"""Stats service: aggregate read-only analytics."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any

from slate.core.stats.schemas import (
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
from slate.infrastructure.cache.base import AbstractCache, NullCache
from slate.infrastructure.cache.keys import NS_STATS, stats_key
from slate.infrastructure.cache.layer import cached_call
from slate.infrastructure.db.repositories.stats import StatsRepository


class StatsService:
    def __init__(
        self,
        stats_repo: StatsRepository,
        cache: AbstractCache | None = None,
        ttl_seconds: int = 300,
    ) -> None:
        self._repo = stats_repo
        self._cache = cache or NullCache()
        self._ttl = ttl_seconds

    async def get_overview(self, user_id: int, user_created_at: datetime) -> StatsOverviewResponse:
        return await cached_call(
            cache=self._cache,
            key=stats_key(user_id, "overview"),
            ttl_seconds=self._ttl,
            namespace=NS_STATS,
            compute=lambda: self._compute_overview(user_id, user_created_at),
            loads=StatsOverviewResponse.model_validate,
            dumps=lambda m: m.model_dump(mode="json"),
        )

    async def _compute_overview(
        self, user_id: int, user_created_at: datetime
    ) -> StatsOverviewResponse:
        total_games = await self._repo.total_games(user_id)
        status_counts = await self._repo.status_counts(user_id)
        play_sessions_30d = await self._repo.play_sessions_last_30d(user_id)
        avg_duration = await self._repo.avg_play_session_duration_minutes(user_id)
        return StatsOverviewResponse(
            total_games=total_games,
            status_counts=status_counts,
            play_sessions_last_30d=play_sessions_30d,
            avg_play_session_duration_minutes=avg_duration,
            user_created_at=user_created_at,
        )

    async def get_play_heatmap(
        self, user_id: int, from_date: date | None, to_date: date | None
    ) -> PlayHeatmapResponse:
        return await cached_call(
            cache=self._cache,
            key=stats_key(user_id, "heatmap", from_date, to_date),
            ttl_seconds=self._ttl,
            namespace=NS_STATS,
            compute=lambda: self._compute_play_heatmap(user_id, from_date, to_date),
            loads=PlayHeatmapResponse.model_validate,
            dumps=lambda m: m.model_dump(mode="json"),
        )

    async def _compute_play_heatmap(
        self, user_id: int, from_date: date | None, to_date: date | None
    ) -> PlayHeatmapResponse:
        play_sessions = await self._repo.ended_play_sessions_in_range(user_id, from_date, to_date)
        # Group by date, compute durations in Python
        day_map: dict[date, dict[str, int]] = defaultdict(lambda: {"count": 0, "total_minutes": 0})
        for m in play_sessions:
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
        return await cached_call(
            cache=self._cache,
            key=stats_key(user_id, "genres"),
            ttl_seconds=self._ttl,
            namespace=NS_STATS,
            compute=lambda: self._compute_genre_stats(user_id),
            loads=GenreStatsResponse.model_validate,
            dumps=lambda m: m.model_dump(mode="json"),
        )

    async def _compute_genre_stats(self, user_id: int) -> GenreStatsResponse:
        play_sessions = await self._repo.ended_play_sessions_with_games(user_id)
        genre_map: dict[str, dict[str, int]] = defaultdict(
            lambda: {"total_minutes": 0, "play_session_count": 0}
        )
        for m in play_sessions:
            duration = int((m.ended_at - m.started_at).total_seconds() / 60) if m.ended_at else 0
            game_genres = m.library_entry.game.genres or []
            for genre in game_genres:
                genre_map[genre]["total_minutes"] += duration
                genre_map[genre]["play_session_count"] += 1

        genre_stats = sorted(
            [
                GenreStat(
                    genre=g,
                    total_minutes=v["total_minutes"],
                    play_session_count=v["play_session_count"],
                )
                for g, v in genre_map.items()
            ],
            key=lambda x: x.total_minutes,
            reverse=True,
        )
        return GenreStatsResponse(genres=genre_stats)

    async def get_platform_stats(self, user_id: int) -> PlatformStatsResponse:
        return await cached_call(
            cache=self._cache,
            key=stats_key(user_id, "platforms"),
            ttl_seconds=self._ttl,
            namespace=NS_STATS,
            compute=lambda: self._compute_platform_stats(user_id),
            loads=PlatformStatsResponse.model_validate,
            dumps=lambda m: m.model_dump(mode="json"),
        )

    async def _compute_platform_stats(self, user_id: int) -> PlatformStatsResponse:
        entries, play_sessions = await self._repo.library_and_play_sessions_for_platforms(user_id)
        # Build platform map from library entries
        plat_map: dict[int, dict[str, Any]] = {}
        for entry in entries:
            pid = entry.platform_id
            if pid not in plat_map:
                plat_map[pid] = {
                    "platform_slug": entry.platform.slug,
                    "platform_label": entry.platform.label,
                    "game_count": 0,
                    "play_session_count": 0,
                    "total_minutes": 0,
                }
            plat_map[pid]["game_count"] += 1

        # Count play_sessions per platform
        for m in play_sessions:
            pid = m.library_entry.platform_id
            if pid in plat_map:
                plat_map[pid]["play_session_count"] += 1
                if m.ended_at:
                    plat_map[pid]["total_minutes"] += int(
                        (m.ended_at - m.started_at).total_seconds() / 60
                    )

        platforms = sorted(
            [PlatformStat(**v) for v in plat_map.values()],
            key=lambda x: x.play_session_count,
            reverse=True,
        )
        return PlatformStatsResponse(platforms=platforms)

    async def get_timeline(
        self, user_id: int, limit: int = 20, offset: int = 0
    ) -> TimelineResponse:
        return await cached_call(
            cache=self._cache,
            key=stats_key(user_id, "timeline", limit, offset),
            ttl_seconds=self._ttl,
            namespace=NS_STATS,
            compute=lambda: self._compute_timeline(user_id, limit, offset),
            loads=TimelineResponse.model_validate,
            dumps=lambda m: m.model_dump(mode="json"),
        )

    async def _compute_timeline(
        self, user_id: int, limit: int = 20, offset: int = 0
    ) -> TimelineResponse:
        play_sessions, total = await self._repo.recent_play_sessions(
            user_id, limit=limit, offset=offset
        )
        items = []
        for m in play_sessions:
            duration = None
            if m.ended_at and m.started_at:
                duration = int((m.ended_at - m.started_at).total_seconds() / 60)
            items.append(
                TimelineEntry(
                    public_id=m.public_id,
                    game_title=m.library_entry.game.title,
                    platform_label=m.library_entry.platform.label,
                    play_session_type=m.play_session_type,
                    recap_text=m.recap_text,
                    wrap_up_text=m.wrap_up_text,
                    ended_via=m.ended_via,
                    started_at=m.started_at,
                    ended_at=m.ended_at,
                    duration_minutes=duration,
                )
            )
        return TimelineResponse(items=items, total=total)
