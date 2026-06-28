"""Repository for the ``loadouts`` table."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from dailyloadout.infrastructure.db.models import Game, LibraryEntry, Loadout, User


class LoadoutRepository:
    """Thin data-access layer around the ``loadouts`` table."""

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
    ) -> Loadout:
        """Insert a new loadout and return it."""
        loadout = Loadout(
            user_id=user_id,
            library_entry_id=library_entry_id,
            mood=mood,
            available_minutes=available_minutes,
            mental_energy=mental_energy,
            reasoning=reasoning,
            context=context,
        )
        self._session.add(loadout)
        await self._session.flush()
        return loadout

    async def get_by_public_id(
        self,
        public_id: UUID,
        user_id: int | None = None,
    ) -> Loadout | None:
        """Return the loadout with *public_id*, optionally scoped to *user_id*."""
        stmt = (
            select(Loadout)
            .options(
                joinedload(Loadout.library_entry).joinedload(LibraryEntry.game),
                joinedload(Loadout.library_entry).joinedload(LibraryEntry.platform),
            )
            .where(Loadout.public_id == public_id)
        )
        if user_id is not None:
            stmt = stmt.where(Loadout.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_pending_for_user(self, user_id: int) -> Loadout | None:
        """Return the most recent loadout with ``action IS NULL`` for the user."""
        stmt = (
            select(Loadout)
            .options(
                joinedload(Loadout.library_entry).joinedload(LibraryEntry.game),
                joinedload(Loadout.library_entry).joinedload(LibraryEntry.platform),
            )
            .where(Loadout.user_id == user_id, Loadout.action.is_(None))
            .order_by(Loadout.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def set_action(self, loadout_id: int, action: str) -> None:
        """Set the action on a loadout."""
        loadout = await self._session.get(Loadout, loadout_id)
        if loadout is not None:
            loadout.action = action
            await self._session.flush()

    async def set_mission(self, loadout_id: int, mission_id: int) -> None:
        """Link a mission to a loadout."""
        loadout = await self._session.get(Loadout, loadout_id)
        if loadout is not None:
            loadout.mission_id = mission_id
            await self._session.flush()

    async def list_for_user(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Loadout]:
        """Return loadouts for *user_id* ordered by newest first."""
        stmt = (
            select(Loadout)
            .options(
                joinedload(Loadout.library_entry).joinedload(LibraryEntry.game),
                joinedload(Loadout.library_entry).joinedload(LibraryEntry.platform),
            )
            .where(Loadout.user_id == user_id)
            .order_by(Loadout.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().unique().all())

    async def count_for_user(self, user_id: int) -> int:
        """Return the total number of loadouts for *user_id*."""
        stmt = select(func.count(Loadout.id)).where(Loadout.user_id == user_id)
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
    ) -> tuple[list[tuple[Loadout, str, str | None]], int]:
        """Return a page of loadouts (each with owner email + game title) + total.

        Spans every user's suggestions. ``query`` matches the owner's email;
        ``action`` filters the lifecycle state — ``"pending"`` maps to the
        un-actioned (``action IS NULL``) rows the auto-ignore worker decays.
        """
        conditions: list[ColumnElement[bool]] = []
        if action == "pending":
            conditions.append(Loadout.action.is_(None))
        elif action:
            conditions.append(Loadout.action == action)
        if query:
            escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            conditions.append(User.email.ilike(f"%{escaped}%"))

        total = (
            await self._session.scalar(
                select(func.count(Loadout.id))
                .join(User, Loadout.user_id == User.id)
                .where(*conditions)
            )
        ) or 0
        result = await self._session.execute(
            select(Loadout, User.email, Game.title)
            .join(User, Loadout.user_id == User.id)
            .outerjoin(LibraryEntry, Loadout.library_entry_id == LibraryEntry.id)
            .outerjoin(Game, LibraryEntry.game_id == Game.id)
            .where(*conditions)
            .order_by(Loadout.created_at.desc(), Loadout.id.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = [(loadout, email, title) for loadout, email, title in result.all()]
        return rows, total

    async def action_counts(self) -> dict[str, int]:
        """Return ``{action: count}`` across all loadouts (NULL → ``"pending"``)."""
        result = await self._session.execute(
            select(Loadout.action, func.count(Loadout.id)).group_by(Loadout.action)
        )
        return {(action or "pending"): count for action, count in result.all()}

    async def get_stale_loadouts(self, max_hours: int = 24) -> list[Loadout]:
        """Return pending loadouts older than *max_hours*."""
        cutoff = datetime.now(UTC) - timedelta(hours=max_hours)
        stmt = select(Loadout).where(
            Loadout.action.is_(None),
            Loadout.created_at < cutoff,
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def mark_ignored(self, loadout_id: int) -> None:
        """Mark a loadout as ignored."""
        loadout = await self._session.get(Loadout, loadout_id)
        if loadout is not None:
            loadout.action = "ignored"
            await self._session.flush()
