"""Repository for the ``games`` table."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from slate.infrastructure.db.like import LIKE_ESCAPE, escape_like
from slate.infrastructure.db.models import Game, LibraryEntry


def _visible_to(user_id: int) -> ColumnElement[bool]:
    """Return the catalogue-visibility predicate for *user_id*.

    A game is browsable by user U when it is canonical (``igdb_id`` set), has
    been promoted to shared, OR was created by U (their own still-private manual
    row). Manual rows stay private to their creator until validated, so one
    account cannot inject offensive/junk titles into everyone's catalogue.
    """
    return or_(
        Game.igdb_id.is_not(None),
        Game.is_shared.is_(True),
        Game.created_by_user_id == user_id,
    )


class GameRepository:
    """Thin data-access layer around the ``games`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count_catalogue(self) -> int:
        """Return how many games are in the shared catalogue (canonical/shared)."""
        stmt = select(func.count(Game.id)).where(
            or_(Game.igdb_id.is_not(None), Game.is_shared.is_(True))
        )
        return (await self._session.scalar(stmt)) or 0

    async def catalogue_counts(self) -> tuple[int, int, int]:
        """Return ``(total, igdb, manual)`` game counts for the admin overview."""
        total = (await self._session.scalar(select(func.count(Game.id)))) or 0
        igdb = (
            await self._session.scalar(
                select(func.count(Game.id)).where(Game.igdb_id.is_not(None))
            )
        ) or 0
        return total, igdb, total - igdb

    async def search_admin(
        self,
        *,
        query: str | None = None,
        is_shared: bool | None = None,
        source: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[tuple[Game, int]], int]:
        """Return a page of games (each with its owner count) plus the total.

        ``source`` filters by provenance: ``"igdb"`` (canonical, ``igdb_id`` set)
        or ``"manual"`` (no ``igdb_id``). ``is_shared`` filters the visibility
        flag. The owner count is how many library entries reference the game —
        the signal an admin weighs before demoting a shared row.
        """
        conditions: list[ColumnElement[bool]] = []
        if query:
            pattern = f"%{escape_like(query)}%"
            conditions.append(
                or_(
                    Game.title.ilike(pattern, escape=LIKE_ESCAPE),
                    Game.slug.ilike(pattern, escape=LIKE_ESCAPE),
                )
            )
        if is_shared is not None:
            conditions.append(Game.is_shared.is_(is_shared))
        if source == "igdb":
            conditions.append(Game.igdb_id.is_not(None))
        elif source == "manual":
            conditions.append(Game.igdb_id.is_(None))

        total = (await self._session.scalar(select(func.count(Game.id)).where(*conditions))) or 0
        owner_count = func.count(LibraryEntry.id)
        result = await self._session.execute(
            select(Game, owner_count)
            .outerjoin(LibraryEntry, LibraryEntry.game_id == Game.id)
            .where(*conditions)
            .group_by(Game.id)
            .order_by(Game.title, Game.id)
            .limit(limit)
            .offset(offset)
        )
        rows = [(game, count) for game, count in result.all()]
        return rows, total

    async def owner_count(self, game_id: int) -> int:
        """Return how many library entries reference *game_id*."""
        total = await self._session.scalar(
            select(func.count(LibraryEntry.id)).where(LibraryEntry.game_id == game_id)
        )
        return total or 0

    async def get_by_id(self, game_id: int) -> Game | None:
        """Return the game with the given internal *game_id*, or ``None``."""
        stmt = select(Game).where(Game.id == game_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_public_id(self, public_id: UUID) -> Game | None:
        """Return the game with the given *public_id*, or ``None``."""
        stmt = select(Game).where(Game.public_id == public_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_igdb_id(self, igdb_id: int) -> Game | None:
        """Return the game with the given *igdb_id*, or ``None``."""
        stmt = select(Game).where(Game.igdb_id == igdb_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Game | None:
        """Return the game with the given *slug*, or ``None``.

        ``slug`` is globally unique, so this returns the single shared catalogue
        row (manual or IGDB) regardless of who created it.
        """
        stmt = select(Game).where(Game.slug == slug)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def search(self, query: str, *, user_id: int, limit: int = 20) -> list[Game]:
        """Search games by title using trigram similarity (ILIKE fallback).

        Only rows VISIBLE to *user_id* are returned (canonical/shared rows plus
        the user's own still-private manual rows); another user's unvalidated
        private manual rows are excluded. Up to *limit* results, by title.
        """
        pattern = f"%{escape_like(query)}%"
        stmt = (
            select(Game)
            .where(Game.title.ilike(pattern, escape=LIKE_ESCAPE), _visible_to(user_id))
            .order_by(Game.title)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self,
        slug: str,
        title: str,
        metadata_source: str,
        igdb_id: int | None = None,
        summary: str | None = None,
        cover_url: str | None = None,
        first_release_date: date | None = None,
        genres: list[str] | None = None,
        created_by_user_id: int | None = None,
        is_shared: bool = False,
    ) -> Game:
        """Insert a new game and return the persisted instance.

        Defaults to *private* (``is_shared=False``): a fresh manual row is visible
        only to its creator until promoted. Callers resolving a canonical IGDB row
        pass ``is_shared=True``.
        """
        game = Game(
            slug=slug,
            title=title,
            metadata_source=metadata_source,
            igdb_id=igdb_id,
            summary=summary,
            cover_url=cover_url,
            first_release_date=first_release_date,
            genres=genres,
            created_by_user_id=created_by_user_id,
            is_shared=is_shared,
        )
        self._session.add(game)
        await self._session.flush()
        return game

    async def list_unenriched(self, limit: int | None = None) -> list[Game]:
        """Return games never enriched from IGDB (``igdb_id IS NULL``).

        These are typically rows created from captures/manual entry before IGDB
        credentials were configured, so they lack genres/cover/summary. Ordered
        by ``id`` for stable, resumable backfills.
        """
        stmt = select(Game).where(Game.igdb_id.is_(None)).order_by(Game.id)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def distinct_genres(self, *, user_id: int) -> list[str]:
        """Return unique genre strings across games VISIBLE to *user_id*, sorted.

        Genres are sourced only from rows the user may browse, so a private manual
        row's genres don't leak into another user's filter list.
        """
        stmt = select(Game.genres).where(Game.genres.is_not(None), _visible_to(user_id))
        result = await self._session.execute(stmt)
        genres: set[str] = set()
        for (game_genres,) in result.all():
            if game_genres:
                genres.update(game_genres)
        return sorted(genres)

    # Identity/ownership columns that a caller-supplied field map must never set,
    # so a widened/`extra`-allowing schema can't become a mass-assignment hole.
    _PROTECTED_FIELDS = frozenset({"id", "public_id", "created_by_user_id", "created_at"})

    async def update(self, game: Game, **fields: object) -> Game:
        """Update the given *game* with the provided fields and flush."""
        for key, value in fields.items():
            if key in self._PROTECTED_FIELDS:
                raise ValueError(f"Field '{key}' cannot be updated")
            setattr(game, key, value)
        await self._session.flush()
        return game

    async def refresh(self, game: Game) -> None:
        """Reload *game* from the DB (e.g. to read the server-recomputed
        ``updated_at`` after an update, which SQLAlchemy expires on flush)."""
        await self._session.refresh(game)
