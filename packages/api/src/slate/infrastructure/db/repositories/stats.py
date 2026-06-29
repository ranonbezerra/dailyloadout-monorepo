"""Repository for stats aggregate queries (read-only)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from slate.infrastructure.db.models import (
    LibraryEntry,
    PlaySession,
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

    async def play_sessions_last_30d(self, user_id: int) -> int:
        cutoff = datetime.now(UTC) - timedelta(days=30)
        stmt = select(func.count(PlaySession.id)).where(
            PlaySession.user_id == user_id,
            PlaySession.started_at >= cutoff,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def avg_play_session_duration_minutes(self, user_id: int) -> float | None:
        """Compute avg duration in Python for SQLite compatibility."""
        stmt = select(PlaySession.started_at, PlaySession.ended_at).where(
            PlaySession.user_id == user_id, PlaySession.ended_at.is_not(None)
        )
        result = await self._session.execute(stmt)
        rows = result.all()
        if not rows:
            return None
        total = sum(float((r.ended_at - r.started_at).total_seconds()) / 60 for r in rows)
        return float(round(total / len(rows), 1))

    async def ended_play_sessions_in_range(
        self, user_id: int, from_date: date | None, to_date: date | None
    ) -> list[PlaySession]:
        stmt = (
            select(PlaySession)
            .where(PlaySession.user_id == user_id, PlaySession.ended_at.is_not(None))
            .order_by(PlaySession.started_at)
        )
        if from_date:
            from_dt = datetime(from_date.year, from_date.month, from_date.day, tzinfo=UTC)
            stmt = stmt.where(PlaySession.started_at >= from_dt)
        if to_date:
            next_day = to_date + timedelta(days=1)
            to_dt = datetime(next_day.year, next_day.month, next_day.day, tzinfo=UTC)
            stmt = stmt.where(PlaySession.started_at < to_dt)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def ended_play_sessions_with_games(self, user_id: int) -> list[PlaySession]:
        stmt = (
            select(PlaySession)
            .options(
                joinedload(PlaySession.library_entry).joinedload(LibraryEntry.game),
            )
            .where(PlaySession.user_id == user_id, PlaySession.ended_at.is_not(None))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().unique().all())

    async def library_and_play_sessions_for_platforms(
        self, user_id: int
    ) -> tuple[list[LibraryEntry], list[PlaySession]]:
        # Load library entries with platform
        entry_stmt = (
            select(LibraryEntry)
            .options(joinedload(LibraryEntry.platform))
            .where(LibraryEntry.user_id == user_id)
        )
        entry_result = await self._session.execute(entry_stmt)
        entries = list(entry_result.scalars().unique().all())

        # Load play_sessions with library entry (for platform_id)
        play_session_stmt = (
            select(PlaySession)
            .options(joinedload(PlaySession.library_entry))
            .where(PlaySession.user_id == user_id, PlaySession.ended_at.is_not(None))
        )
        play_session_result = await self._session.execute(play_session_stmt)
        play_sessions = list(play_session_result.scalars().unique().all())

        return entries, play_sessions

    async def recent_play_sessions(
        self, user_id: int, limit: int = 20, offset: int = 0
    ) -> tuple[list[PlaySession], int]:
        stmt = (
            select(PlaySession)
            .options(
                joinedload(PlaySession.library_entry).joinedload(LibraryEntry.game),
                joinedload(PlaySession.library_entry).joinedload(LibraryEntry.platform),
            )
            .where(PlaySession.user_id == user_id, PlaySession.ended_at.is_not(None))
            .order_by(PlaySession.ended_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        play_sessions = list(result.scalars().unique().all())

        count_stmt = select(func.count(PlaySession.id)).where(
            PlaySession.user_id == user_id, PlaySession.ended_at.is_not(None)
        )
        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar_one()

        return play_sessions, total
