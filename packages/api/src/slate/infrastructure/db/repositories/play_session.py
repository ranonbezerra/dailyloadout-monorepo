"""Repository for the ``play_sessions`` table."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from slate.infrastructure.db.models import Game, LibraryEntry, PlaySession, User


class PlaySessionRepository:
    """Thin data-access layer around the ``play_sessions`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        """The underlying session, so sibling repos can share this unit of work."""
        return self._session

    async def create(
        self,
        user_id: int,
        library_entry_id: int,
        recap_text: str | None = None,
    ) -> PlaySession:
        """Insert a new play_session and return it."""
        play_session = PlaySession(
            user_id=user_id,
            library_entry_id=library_entry_id,
            recap_text=recap_text,
        )
        self._session.add(play_session)
        await self._session.flush()
        return play_session

    async def create_retroactive(
        self,
        user_id: int,
        library_entry_id: int,
        wrap_up_text: str,
        extracted_state: dict[str, Any] | None = None,
    ) -> PlaySession:
        """Insert a pre-ended retroactive play_session and return it."""
        now = datetime.now(UTC)
        play_session = PlaySession(
            user_id=user_id,
            library_entry_id=library_entry_id,
            play_session_type="retroactive",
            wrap_up_text=wrap_up_text,
            extracted_state=extracted_state,
            ended_via="retroactive",
            started_at=now,
            ended_at=now,
        )
        self._session.add(play_session)
        await self._session.flush()
        return play_session

    async def get_by_public_id(
        self,
        public_id: UUID,
        user_id: int | None = None,
    ) -> PlaySession | None:
        """Return the play_session with *public_id*, optionally scoped to *user_id*.

        Eagerly loads the library entry with its game and platform.
        """
        stmt = (
            select(PlaySession)
            .options(
                joinedload(PlaySession.library_entry).joinedload(LibraryEntry.game),
                joinedload(PlaySession.library_entry).joinedload(LibraryEntry.platform),
            )
            .where(PlaySession.public_id == public_id)
        )
        if user_id is not None:
            stmt = stmt.where(PlaySession.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_active_for_user(self, user_id: int) -> PlaySession | None:
        """Return the user's currently active (un-ended) play_session, or ``None``."""
        stmt = (
            select(PlaySession)
            .options(
                joinedload(PlaySession.library_entry).joinedload(LibraryEntry.game),
                joinedload(PlaySession.library_entry).joinedload(LibraryEntry.platform),
            )
            .where(PlaySession.user_id == user_id, PlaySession.ended_at.is_(None))
        )
        result = await self._session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_recent_for_entry(
        self,
        library_entry_id: int,
        limit: int = 3,
    ) -> list[PlaySession]:
        """Return the most recent *ended* play_sessions for a library entry.

        Only returns play_sessions that have ``extracted_state`` set (i.e.
        wrap_ups that have been processed).
        """
        stmt = (
            select(PlaySession)
            .where(
                PlaySession.library_entry_id == library_entry_id,
                PlaySession.ended_at.is_not(None),
                PlaySession.extracted_state.is_not(None),
            )
            .order_by(PlaySession.ended_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_for_user(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> list[PlaySession]:
        """Return play_sessions for *user_id* ordered by newest first."""
        stmt = (
            select(PlaySession)
            .options(
                joinedload(PlaySession.library_entry).joinedload(LibraryEntry.game),
                joinedload(PlaySession.library_entry).joinedload(LibraryEntry.platform),
            )
            .where(PlaySession.user_id == user_id)
            .order_by(PlaySession.started_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().unique().all())

    async def count_for_user(self, user_id: int) -> int:
        """Return the total number of play_sessions for *user_id*."""
        stmt = select(func.count(PlaySession.id)).where(PlaySession.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def count_active(self) -> int:
        """Return how many play_sessions are active (not ended) across all users."""
        stmt = select(func.count(PlaySession.id)).where(PlaySession.ended_at.is_(None))
        return (await self._session.scalar(stmt)) or 0

    # ── Backoffice (admin) ──
    async def search_admin(
        self,
        *,
        query: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[tuple[PlaySession, str, str | None]], int]:
        """Return a page of play_sessions (each with owner email + game title) + total.

        Spans every user's play_sessions. ``query`` matches the owner's email;
        ``status`` is the derived lifecycle state (``active`` = un-ended,
        ``ended`` = closed).
        """
        conditions: list[ColumnElement[bool]] = []
        if status == "active":
            conditions.append(PlaySession.ended_at.is_(None))
        elif status == "ended":
            conditions.append(PlaySession.ended_at.is_not(None))
        if query:
            escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            conditions.append(User.email.ilike(f"%{escaped}%"))

        total = (
            await self._session.scalar(
                select(func.count(PlaySession.id))
                .join(User, PlaySession.user_id == User.id)
                .where(*conditions)
            )
        ) or 0
        result = await self._session.execute(
            select(PlaySession, User.email, Game.title)
            .join(User, PlaySession.user_id == User.id)
            .join(LibraryEntry, PlaySession.library_entry_id == LibraryEntry.id)
            .outerjoin(Game, LibraryEntry.game_id == Game.id)
            .where(*conditions)
            .order_by(PlaySession.started_at.desc(), PlaySession.id.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = [(play_session, email, title) for play_session, email, title in result.all()]
        return rows, total

    async def status_counts(self) -> dict[str, int]:
        """Return ``{"active": n, "ended": m}`` across all play_sessions."""
        active = await self.count_active()
        total = (await self._session.scalar(select(func.count(PlaySession.id)))) or 0
        return {"active": active, "ended": total - active}

    async def set_wrap_up(
        self,
        play_session_id: int,
        wrap_up_text: str,
    ) -> None:
        """Set the user's wrap_up text on a play_session."""
        play_session = await self._session.get(PlaySession, play_session_id)
        if play_session is not None:
            play_session.wrap_up_text = wrap_up_text
            await self._session.flush()

    async def set_extracted_state(
        self,
        play_session_id: int,
        extracted_state: Mapping[str, object],
    ) -> None:
        """Set the LLM-extracted state on a play_session."""
        play_session = await self._session.get(PlaySession, play_session_id)
        if play_session is not None:
            play_session.extracted_state = dict(extracted_state)
            await self._session.flush()

    async def end_play_session(
        self,
        play_session_id: int,
        ended_via: str,
        ended_at: datetime | None = None,
    ) -> None:
        """Mark a play_session as ended."""
        play_session = await self._session.get(PlaySession, play_session_id)
        if play_session is not None:
            play_session.ended_via = ended_via
            play_session.ended_at = ended_at or datetime.now(UTC)
            await self._session.flush()

    async def set_recap(
        self,
        play_session_id: int,
        recap_text: str,
    ) -> None:
        """Update the recap text of a play_session."""
        play_session = await self._session.get(PlaySession, play_session_id)
        if play_session is not None:
            play_session.recap_text = recap_text
            await self._session.flush()

    async def get_pending_extractions(
        self,
        library_entry_id: int,
    ) -> list[PlaySession]:
        """Return ended play_sessions with wrap_up text but no extracted state.

        These are play_sessions where the async extraction task hasn't completed
        (or failed). Used by the sync fallback before recap generation.
        """
        stmt = (
            select(PlaySession)
            .options(
                joinedload(PlaySession.library_entry).joinedload(LibraryEntry.game),
                joinedload(PlaySession.library_entry).joinedload(LibraryEntry.platform),
            )
            .where(
                PlaySession.library_entry_id == library_entry_id,
                PlaySession.ended_at.is_not(None),
                PlaySession.wrap_up_text.is_not(None),
                PlaySession.extracted_state.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_stale_play_sessions(self, max_hours: int = 8) -> list[PlaySession]:
        """Return active play_sessions older than *max_hours*."""
        cutoff = datetime.now(UTC) - timedelta(hours=max_hours)
        stmt = select(PlaySession).where(
            PlaySession.ended_at.is_(None),
            PlaySession.started_at < cutoff,
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def auto_clamp(self, play_session_id: int, max_hours: int = 8) -> None:
        """Auto-clamp a stale play_session."""
        play_session = await self._session.get(PlaySession, play_session_id)
        if play_session is not None:
            play_session.ended_via = "auto_clamp"
            play_session.ended_at = play_session.started_at + timedelta(hours=max_hours)
            await self._session.flush()
