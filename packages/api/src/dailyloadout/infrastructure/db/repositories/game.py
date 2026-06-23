"""Repository for the ``games`` table."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dailyloadout.infrastructure.db.models import Game


class GameRepository:
    """Thin data-access layer around the ``games`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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
        """Return the game with the given *slug*, or ``None``."""
        stmt = select(Game).where(Game.slug == slug)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def search(self, query: str, limit: int = 20) -> list[Game]:
        """Search games by title using trigram similarity (ILIKE fallback).

        Returns up to *limit* results ordered by relevance.
        """
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        stmt = select(Game).where(Game.title.ilike(pattern)).order_by(Game.title).limit(limit)
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
    ) -> Game:
        """Insert a new game and return the persisted instance."""
        game = Game(
            slug=slug,
            title=title,
            metadata_source=metadata_source,
            igdb_id=igdb_id,
            summary=summary,
            cover_url=cover_url,
            first_release_date=first_release_date,
            genres=genres,
        )
        self._session.add(game)
        await self._session.flush()
        return game

    async def distinct_genres(self) -> list[str]:
        """Return all unique genre strings across all games, sorted."""
        stmt = select(Game.genres).where(Game.genres.is_not(None))
        result = await self._session.execute(stmt)
        genres: set[str] = set()
        for (game_genres,) in result.all():
            if game_genres:
                genres.update(game_genres)
        return sorted(genres)

    async def update(self, game: Game, **fields: object) -> Game:
        """Update the given *game* with the provided fields and flush."""
        for key, value in fields.items():
            setattr(game, key, value)
        await self._session.flush()
        return game
