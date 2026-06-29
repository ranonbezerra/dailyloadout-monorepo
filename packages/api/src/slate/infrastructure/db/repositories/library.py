"""Repository for the ``library_entries`` table."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from slate.infrastructure.db.models import LibraryEntry, PlaySession


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

    async def count_games_for_user(self, user_id: int, status: str | None = None) -> int:
        """Return the number of DISTINCT games in *user_id*'s library.

        Counts games, not per-platform entries, so it matches the page size of
        :meth:`list_grouped_for_user` for game-level pagination. The optional
        *status* filter restricts the games considered to those with at least
        one entry in that status.
        """
        stmt = select(func.count(func.distinct(LibraryEntry.game_id))).where(
            LibraryEntry.user_id == user_id
        )
        if status is not None:
            stmt = stmt.where(LibraryEntry.status == status)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def list_grouped_for_user(
        self,
        user_id: int,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[LibraryEntry]:
        """Return entries for one page of games, ordered for grouping.

        Strategy (two queries, no N+1 regardless of platform count):

        1. A *game-id page* query selects the user's distinct ``game_id``s,
           ordered by most-recently-touched game first
           (``MAX(last_played_at)`` then ``MAX(created_at)``), with
           ``offset`` / ``limit`` applied — so pagination is BY GAME.
        2. A single *entries* query loads every entry (joinedload game +
           platform) for exactly those game ids, ordered the same way so the
           service can group sequentially.

        When *status* is given, both the game-id page and the loaded entries are
        restricted to that status, so a filtered view only surfaces the matching
        platform states (and only games that have one).
        """
        game_order_touched = func.max(
            func.coalesce(LibraryEntry.last_played_at, LibraryEntry.created_at)
        ).label("touched_at")
        game_order_created = func.max(LibraryEntry.created_at).label("created_at_max")

        page_stmt = select(
            LibraryEntry.game_id,
            game_order_touched,
            game_order_created,
        ).where(LibraryEntry.user_id == user_id)
        if status is not None:
            page_stmt = page_stmt.where(LibraryEntry.status == status)
        page_stmt = (
            page_stmt.group_by(LibraryEntry.game_id)
            .order_by(game_order_touched.desc(), game_order_created.desc())
            .offset(offset)
            .limit(limit)
        )
        page_result = await self._session.execute(page_stmt)
        ordered_game_ids = [row.game_id for row in page_result.all()]
        if not ordered_game_ids:
            return []

        entries_stmt = (
            select(LibraryEntry)
            .options(joinedload(LibraryEntry.game), joinedload(LibraryEntry.platform))
            .where(
                LibraryEntry.user_id == user_id,
                LibraryEntry.game_id.in_(ordered_game_ids),
            )
        )
        if status is not None:
            entries_stmt = entries_stmt.where(LibraryEntry.status == status)
        entries_result = await self._session.execute(entries_stmt)
        entries = list(entries_result.scalars().unique().all())

        # Preserve the game-level order computed in the page query; within a
        # game, order platforms by label for a stable client-facing list.
        rank = {game_id: index for index, game_id in enumerate(ordered_game_ids)}
        entries.sort(key=lambda e: (rank[e.game_id], e.platform.label))
        return entries

    async def list_for_user_game(self, user_id: int, game_id: int) -> list[LibraryEntry]:
        """Return all of *user_id*'s entries for a single *game_id*.

        Eagerly loads game + platform so the caller can serialize a grouped row
        without further queries.
        """
        stmt = (
            select(LibraryEntry)
            .options(joinedload(LibraryEntry.game), joinedload(LibraryEntry.platform))
            .where(
                LibraryEntry.user_id == user_id,
                LibraryEntry.game_id == game_id,
            )
        )
        result = await self._session.execute(stmt)
        entries = list(result.scalars().unique().all())
        entries.sort(key=lambda e: e.platform.label)
        return entries

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

    async def list_eligible_for_pick(
        self,
        user_id: int,
        cooldown_hours: int = 12,
    ) -> list[LibraryEntry]:
        """Return entries eligible for a Pick.

        An entry is eligible when:
        - ``status`` is ``backlog``, ``playing``, or ``paused``
        - No play_session on that entry ended within the last *cooldown_hours*
        """
        recent_cutoff = datetime.now(UTC) - timedelta(hours=cooldown_hours)

        # Subquery: entry IDs with a play_session ended within the cooldown window.
        recently_ended = (
            select(PlaySession.library_entry_id)
            .where(
                PlaySession.ended_at.is_not(None),
                PlaySession.ended_at > recent_cutoff,
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

    async def count_distinct_owners(self, game_id: int) -> int:
        """Return the number of DISTINCT users who own *game_id* (any platform).

        Drives the catalogue promotion path: a private manual row becomes globally
        shared once enough independent users own it (anti-abuse Block C).
        """
        stmt = select(func.count(func.distinct(LibraryEntry.user_id))).where(
            LibraryEntry.game_id == game_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

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
