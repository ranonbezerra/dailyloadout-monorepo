"""Repository for stats aggregate queries (read-only)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from dailyloadout.infrastructure.db.models import (
    LibraryEntry,
    Mission,
)


class StatsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def total_games(self, user_id: int) -> int:
        stmt = select(func.count(LibraryEntry.id)).where(LibraryEntry.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def status_counts(self, user_id: int) -> dict[str, int]:
        stmt = (
            select(LibraryEntry.status, func.count(LibraryEntry.id))
            .where(LibraryEntry.user_id == user_id)
            .group_by(LibraryEntry.status)
        )
        result = await self._session.execute(stmt)
        return {str(status): count for status, count in result.all()}

    async def missions_last_30d(self, user_id: int) -> int:
        cutoff = datetime.now(UTC) - timedelta(days=30)
        stmt = select(func.count(Mission.id)).where(
            Mission.user_id == user_id,
            Mission.started_at >= cutoff,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def avg_mission_duration_minutes(self, user_id: int) -> float | None:
        """Compute avg duration in Python for SQLite compatibility."""
        stmt = select(Mission.started_at, Mission.ended_at).where(
            Mission.user_id == user_id, Mission.ended_at.is_not(None)
        )
        result = await self._session.execute(stmt)
        rows = result.all()
        if not rows:
            return None
        total = sum(float((r.ended_at - r.started_at).total_seconds()) / 60 for r in rows)
        return float(round(total / len(rows), 1))

    async def ended_missions_in_range(
        self, user_id: int, from_date: date | None, to_date: date | None
    ) -> list[Mission]:
        stmt = (
            select(Mission)
            .where(Mission.user_id == user_id, Mission.ended_at.is_not(None))
            .order_by(Mission.started_at)
        )
        if from_date:
            from_dt = datetime(from_date.year, from_date.month, from_date.day, tzinfo=UTC)
            stmt = stmt.where(Mission.started_at >= from_dt)
        if to_date:
            next_day = to_date + timedelta(days=1)
            to_dt = datetime(next_day.year, next_day.month, next_day.day, tzinfo=UTC)
            stmt = stmt.where(Mission.started_at < to_dt)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def ended_missions_with_games(self, user_id: int) -> list[Mission]:
        stmt = (
            select(Mission)
            .options(
                joinedload(Mission.library_entry).joinedload(LibraryEntry.game),
            )
            .where(Mission.user_id == user_id, Mission.ended_at.is_not(None))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().unique().all())

    async def library_and_missions_for_platforms(
        self, user_id: int
    ) -> tuple[list[LibraryEntry], list[Mission]]:
        # Load library entries with platform
        entry_stmt = (
            select(LibraryEntry)
            .options(joinedload(LibraryEntry.platform))
            .where(LibraryEntry.user_id == user_id)
        )
        entry_result = await self._session.execute(entry_stmt)
        entries = list(entry_result.scalars().unique().all())

        # Load missions with library entry (for platform_id)
        mission_stmt = (
            select(Mission)
            .options(joinedload(Mission.library_entry))
            .where(Mission.user_id == user_id, Mission.ended_at.is_not(None))
        )
        mission_result = await self._session.execute(mission_stmt)
        missions = list(mission_result.scalars().unique().all())

        return entries, missions

    async def recent_missions(
        self, user_id: int, limit: int = 20, offset: int = 0
    ) -> tuple[list[Mission], int]:
        stmt = (
            select(Mission)
            .options(
                joinedload(Mission.library_entry).joinedload(LibraryEntry.game),
                joinedload(Mission.library_entry).joinedload(LibraryEntry.platform),
            )
            .where(Mission.user_id == user_id, Mission.ended_at.is_not(None))
            .order_by(Mission.ended_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        missions = list(result.scalars().unique().all())

        count_stmt = select(func.count(Mission.id)).where(
            Mission.user_id == user_id, Mission.ended_at.is_not(None)
        )
        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar_one()

        return missions, total
