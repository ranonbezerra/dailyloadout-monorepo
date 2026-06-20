"""Repository for the ``library_entries`` table."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from dailyloadout.infrastructure.db.models import LibraryEntry, Mission


class LibraryRepository:
    """Thin data-access layer around the ``library_entries`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_public_id(self, public_id: UUID, user_id: int) -> LibraryEntry | None:
        """Return the library entry owned by *user_id* with *public_id*, or ``None``."""
        stmt = (
            select(LibraryEntry)
            .options(joinedload(LibraryEntry.game), joinedload(LibraryEntry.platform))
            .where(
                LibraryEntry.public_id == public_id,
                LibraryEntry.user_id == user_id,
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: int,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[LibraryEntry]:
        """Return library entries for *user_id*, eagerly loading game and platform."""
        stmt = (
            select(LibraryEntry)
            .options(joinedload(LibraryEntry.game), joinedload(LibraryEntry.platform))
            .where(LibraryEntry.user_id == user_id)
        )
        if status is not None:
            stmt = stmt.where(LibraryEntry.status == status)
        stmt = stmt.order_by(LibraryEntry.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().unique().all())

    async def count_for_user(self, user_id: int, status: str | None = None) -> int:
        """Return the total number of library entries for *user_id*."""
        stmt = select(func.count(LibraryEntry.id)).where(LibraryEntry.user_id == user_id)
        if status is not None:
            stmt = stmt.where(LibraryEntry.status == status)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def create(
        self,
        user_id: int,
        game_id: int,
        platform_id: int,
        status: str = "backlog",
        notes: str | None = None,
        acquired_at: date | None = None,
    ) -> LibraryEntry:
        """Insert a new library entry and return it."""
        entry = LibraryEntry(
            user_id=user_id,
            game_id=game_id,
            platform_id=platform_id,
            status=status,
            notes=notes,
            acquired_at=acquired_at,
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def update(self, entry: LibraryEntry, **fields: object) -> LibraryEntry:
        """Apply *fields* to *entry* and flush the changes."""
        for key, value in fields.items():
            setattr(entry, key, value)
        await self._session.flush()
        await self._session.refresh(entry, attribute_names=["updated_at"])
        return entry

    async def delete(self, entry: LibraryEntry) -> None:
        """Remove *entry* from the database."""
        stmt = delete(LibraryEntry).where(LibraryEntry.id == entry.id)
        await self._session.execute(stmt)

    async def list_eligible_for_loadout(
        self,
        user_id: int,
        cooldown_hours: int = 12,
    ) -> list[LibraryEntry]:
        """Return entries eligible for a daily loadout suggestion.

        An entry is eligible when:
        - ``status`` is ``backlog``, ``playing``, or ``paused``
        - No mission on that entry ended within the last *cooldown_hours*
        """
        recent_cutoff = datetime.now(UTC) - timedelta(hours=cooldown_hours)

        # Subquery: entry IDs with a mission ended within the cooldown window.
        recently_ended = (
            select(Mission.library_entry_id)
            .where(
                Mission.ended_at.is_not(None),
                Mission.ended_at > recent_cutoff,
            )
            .subquery()
        )

        stmt = (
            select(LibraryEntry)
            .options(joinedload(LibraryEntry.game), joinedload(LibraryEntry.platform))
            .where(
                LibraryEntry.user_id == user_id,
                LibraryEntry.status.in_(["backlog", "playing", "paused"]),
                LibraryEntry.id.not_in(select(recently_ended.c.library_entry_id)),
            )
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().unique().all())

    async def exists(self, user_id: int, game_id: int, platform_id: int) -> bool:
        """Return ``True`` if an entry for the given triple already exists."""
        stmt = (
            select(LibraryEntry.id)
            .where(
                LibraryEntry.user_id == user_id,
                LibraryEntry.game_id == game_id,
                LibraryEntry.platform_id == platform_id,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
