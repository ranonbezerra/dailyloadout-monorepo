"""Repository for the ``missions`` table."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from dailyloadout.infrastructure.db.models import Game, LibraryEntry, Mission, User


class MissionRepository:
    """Thin data-access layer around the ``missions`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        user_id: int,
        library_entry_id: int,
        briefing_text: str | None = None,
    ) -> Mission:
        """Insert a new mission and return it."""
        mission = Mission(
            user_id=user_id,
            library_entry_id=library_entry_id,
            briefing_text=briefing_text,
        )
        self._session.add(mission)
        await self._session.flush()
        return mission

    async def create_retroactive(
        self,
        user_id: int,
        library_entry_id: int,
        debrief_text: str,
        extracted_state: dict[str, Any] | None = None,
    ) -> Mission:
        """Insert a pre-ended retroactive mission and return it."""
        now = datetime.now(UTC)
        mission = Mission(
            user_id=user_id,
            library_entry_id=library_entry_id,
            mission_type="retroactive",
            debrief_text=debrief_text,
            extracted_state=extracted_state,
            ended_via="retroactive",
            started_at=now,
            ended_at=now,
        )
        self._session.add(mission)
        await self._session.flush()
        return mission

    async def get_by_public_id(
        self,
        public_id: UUID,
        user_id: int | None = None,
    ) -> Mission | None:
        """Return the mission with *public_id*, optionally scoped to *user_id*.

        Eagerly loads the library entry with its game and platform.
        """
        stmt = (
            select(Mission)
            .options(
                joinedload(Mission.library_entry).joinedload(LibraryEntry.game),
                joinedload(Mission.library_entry).joinedload(LibraryEntry.platform),
            )
            .where(Mission.public_id == public_id)
        )
        if user_id is not None:
            stmt = stmt.where(Mission.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_active_for_user(self, user_id: int) -> Mission | None:
        """Return the user's currently active (un-ended) mission, or ``None``."""
        stmt = (
            select(Mission)
            .options(
                joinedload(Mission.library_entry).joinedload(LibraryEntry.game),
                joinedload(Mission.library_entry).joinedload(LibraryEntry.platform),
            )
            .where(Mission.user_id == user_id, Mission.ended_at.is_(None))
        )
        result = await self._session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_recent_for_entry(
        self,
        library_entry_id: int,
        limit: int = 3,
    ) -> list[Mission]:
        """Return the most recent *ended* missions for a library entry.

        Only returns missions that have ``extracted_state`` set (i.e.
        debriefs that have been processed).
        """
        stmt = (
            select(Mission)
            .where(
                Mission.library_entry_id == library_entry_id,
                Mission.ended_at.is_not(None),
                Mission.extracted_state.is_not(None),
            )
            .order_by(Mission.ended_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_for_user(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Mission]:
        """Return missions for *user_id* ordered by newest first."""
        stmt = (
            select(Mission)
            .options(
                joinedload(Mission.library_entry).joinedload(LibraryEntry.game),
                joinedload(Mission.library_entry).joinedload(LibraryEntry.platform),
            )
            .where(Mission.user_id == user_id)
            .order_by(Mission.started_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().unique().all())

    async def count_for_user(self, user_id: int) -> int:
        """Return the total number of missions for *user_id*."""
        stmt = select(func.count(Mission.id)).where(Mission.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def count_active(self) -> int:
        """Return how many missions are active (not ended) across all users."""
        stmt = select(func.count(Mission.id)).where(Mission.ended_at.is_(None))
        return (await self._session.scalar(stmt)) or 0

    # ── Backoffice (admin) ──
    async def search_admin(
        self,
        *,
        query: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[tuple[Mission, str, str | None]], int]:
        """Return a page of missions (each with owner email + game title) + total.

        Spans every user's missions. ``query`` matches the owner's email;
        ``status`` is the derived lifecycle state (``active`` = un-ended,
        ``ended`` = closed).
        """
        conditions: list[ColumnElement[bool]] = []
        if status == "active":
            conditions.append(Mission.ended_at.is_(None))
        elif status == "ended":
            conditions.append(Mission.ended_at.is_not(None))
        if query:
            escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            conditions.append(User.email.ilike(f"%{escaped}%"))

        total = (
            await self._session.scalar(
                select(func.count(Mission.id))
                .join(User, Mission.user_id == User.id)
                .where(*conditions)
            )
        ) or 0
        result = await self._session.execute(
            select(Mission, User.email, Game.title)
            .join(User, Mission.user_id == User.id)
            .join(LibraryEntry, Mission.library_entry_id == LibraryEntry.id)
            .outerjoin(Game, LibraryEntry.game_id == Game.id)
            .where(*conditions)
            .order_by(Mission.started_at.desc(), Mission.id.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = [(mission, email, title) for mission, email, title in result.all()]
        return rows, total

    async def status_counts(self) -> dict[str, int]:
        """Return ``{"active": n, "ended": m}`` across all missions."""
        active = await self.count_active()
        total = (await self._session.scalar(select(func.count(Mission.id)))) or 0
        return {"active": active, "ended": total - active}

    async def set_debrief(
        self,
        mission_id: int,
        debrief_text: str,
    ) -> None:
        """Set the user's debrief text on a mission."""
        mission = await self._session.get(Mission, mission_id)
        if mission is not None:
            mission.debrief_text = debrief_text
            await self._session.flush()

    async def set_extracted_state(
        self,
        mission_id: int,
        extracted_state: Mapping[str, object],
    ) -> None:
        """Set the LLM-extracted state on a mission."""
        mission = await self._session.get(Mission, mission_id)
        if mission is not None:
            mission.extracted_state = dict(extracted_state)
            await self._session.flush()

    async def end_mission(
        self,
        mission_id: int,
        ended_via: str,
        ended_at: datetime | None = None,
    ) -> None:
        """Mark a mission as ended."""
        mission = await self._session.get(Mission, mission_id)
        if mission is not None:
            mission.ended_via = ended_via
            mission.ended_at = ended_at or datetime.now(UTC)
            await self._session.flush()

    async def set_briefing(
        self,
        mission_id: int,
        briefing_text: str,
    ) -> None:
        """Update the briefing text of a mission."""
        mission = await self._session.get(Mission, mission_id)
        if mission is not None:
            mission.briefing_text = briefing_text
            await self._session.flush()

    async def get_pending_extractions(
        self,
        library_entry_id: int,
    ) -> list[Mission]:
        """Return ended missions with debrief text but no extracted state.

        These are missions where the async extraction task hasn't completed
        (or failed). Used by the sync fallback before briefing generation.
        """
        stmt = (
            select(Mission)
            .options(
                joinedload(Mission.library_entry).joinedload(LibraryEntry.game),
                joinedload(Mission.library_entry).joinedload(LibraryEntry.platform),
            )
            .where(
                Mission.library_entry_id == library_entry_id,
                Mission.ended_at.is_not(None),
                Mission.debrief_text.is_not(None),
                Mission.extracted_state.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_stale_missions(self, max_hours: int = 8) -> list[Mission]:
        """Return active missions older than *max_hours*."""
        cutoff = datetime.now(UTC) - timedelta(hours=max_hours)
        stmt = select(Mission).where(
            Mission.ended_at.is_(None),
            Mission.started_at < cutoff,
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def auto_clamp(self, mission_id: int, max_hours: int = 8) -> None:
        """Auto-clamp a stale mission."""
        mission = await self._session.get(Mission, mission_id)
        if mission is not None:
            mission.ended_via = "auto_clamp"
            mission.ended_at = mission.started_at + timedelta(hours=max_hours)
            await self._session.flush()
