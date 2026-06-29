"""Repository for the ``picks`` table."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from slate.infrastructure.db.models import Game, LibraryEntry, Pick, User


class PickRepository:
    """Thin data-access layer around the ``picks`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        user_id: int,
        library_entry_id: int,
        mood: str,
        available_minutes: int,
        mental_energy: str,
        reasoning: str | None = None,
        context: str | None = None,
    ) -> Pick:
        """Insert a new pick and return it."""
        pick = Pick(
            user_id=user_id,
            library_entry_id=library_entry_id,
            mood=mood,
            available_minutes=available_minutes,
            mental_energy=mental_energy,
            reasoning=reasoning,
            context=context,
        )
        self._session.add(pick)
        await self._session.flush()
        return pick

    async def get_by_public_id(
        self,
        public_id: UUID,
        user_id: int | None = None,
    ) -> Pick | None:
        """Return the pick with *public_id*, optionally scoped to *user_id*."""
        stmt = (
            select(Pick)
            .options(
                joinedload(Pick.library_entry).joinedload(LibraryEntry.game),
                joinedload(Pick.library_entry).joinedload(LibraryEntry.platform),
            )
            .where(Pick.public_id == public_id)
        )
        if user_id is not None:
            stmt = stmt.where(Pick.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_pending_for_user(self, user_id: int) -> Pick | None:
        """Return the most recent pick with ``action IS NULL`` for the user."""
        stmt = (
            select(Pick)
            .options(
                joinedload(Pick.library_entry).joinedload(LibraryEntry.game),
                joinedload(Pick.library_entry).joinedload(LibraryEntry.platform),
            )
            .where(Pick.user_id == user_id, Pick.action.is_(None))
            .order_by(Pick.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def set_action(self, pick_id: int, action: str) -> None:
        """Set the action on a pick."""
        pick = await self._session.get(Pick, pick_id)
        if pick is not None:
            pick.action = action
            await self._session.flush()

    async def set_play_session(self, pick_id: int, play_session_id: int) -> None:
        """Link a play_session to a pick."""
        pick = await self._session.get(Pick, pick_id)
        if pick is not None:
            pick.play_session_id = play_session_id
            await self._session.flush()

    async def list_for_user(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Pick]:
        """Return picks for *user_id* ordered by newest first."""
        stmt = (
            select(Pick)
            .options(
                joinedload(Pick.library_entry).joinedload(LibraryEntry.game),
                joinedload(Pick.library_entry).joinedload(LibraryEntry.platform),
            )
            .where(Pick.user_id == user_id)
            .order_by(Pick.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().unique().all())

    async def count_for_user(self, user_id: int) -> int:
        """Return the total number of picks for *user_id*."""
        stmt = select(func.count(Pick.id)).where(Pick.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    # ── Backoffice (admin) ──
    async def search_admin(
        self,
        *,
        query: str | None = None,
        action: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[tuple[Pick, str, str | None]], int]:
        """Return a page of picks (each with owner email + game title) + total.

        Spans every user's suggestions. ``query`` matches the owner's email;
        ``action`` filters the lifecycle state — ``"pending"`` maps to the
        un-actioned (``action IS NULL``) rows the auto-ignore worker decays.
        """
        conditions: list[ColumnElement[bool]] = []
        if action == "pending":
            conditions.append(Pick.action.is_(None))
        elif action:
            conditions.append(Pick.action == action)
        if query:
            escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            conditions.append(User.email.ilike(f"%{escaped}%"))

        total = (
            await self._session.scalar(
                select(func.count(Pick.id)).join(User, Pick.user_id == User.id).where(*conditions)
            )
        ) or 0
        result = await self._session.execute(
            select(Pick, User.email, Game.title)
            .join(User, Pick.user_id == User.id)
            .outerjoin(LibraryEntry, Pick.library_entry_id == LibraryEntry.id)
            .outerjoin(Game, LibraryEntry.game_id == Game.id)
            .where(*conditions)
            .order_by(Pick.created_at.desc(), Pick.id.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = [(pick, email, title) for pick, email, title in result.all()]
        return rows, total

    async def action_counts(self) -> dict[str, int]:
        """Return ``{action: count}`` across all picks (NULL → ``"pending"``)."""
        result = await self._session.execute(
            select(Pick.action, func.count(Pick.id)).group_by(Pick.action)
        )
        return {(action or "pending"): count for action, count in result.all()}

    async def get_stale_picks(self, max_hours: int = 24) -> list[Pick]:
        """Return pending picks older than *max_hours*."""
        cutoff = datetime.now(UTC) - timedelta(hours=max_hours)
        stmt = select(Pick).where(
            Pick.action.is_(None),
            Pick.created_at < cutoff,
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def mark_ignored(self, pick_id: int) -> None:
        """Mark a pick as ignored."""
        pick = await self._session.get(Pick, pick_id)
        if pick is not None:
            pick.action = "ignored"
            await self._session.flush()
