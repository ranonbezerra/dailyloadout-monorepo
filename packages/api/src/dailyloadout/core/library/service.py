"""Library service: game management, library CRUD operations."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from dailyloadout.infrastructure.db.models import Game, LibraryEntry, Platform
from dailyloadout.infrastructure.db.repositories.game import GameRepository
from dailyloadout.infrastructure.db.repositories.library import LibraryRepository
from dailyloadout.infrastructure.db.repositories.platform import PlatformRepository


class LibraryService:
    """Orchestrates game catalog and user library operations."""

    def __init__(
        self,
        game_repo: GameRepository,
        library_repo: LibraryRepository,
        platform_repo: PlatformRepository,
    ) -> None:
        self._game_repo = game_repo
        self._library_repo = library_repo
        self._platform_repo = platform_repo

    # ------------------------------------------------------------------
    # Games
    # ------------------------------------------------------------------
    async def create_game(
        self,
        slug: str,
        title: str,
        metadata_source: str = "manual",
        igdb_id: int | None = None,
        summary: str | None = None,
        cover_url: str | None = None,
        first_release_date: date | None = None,
        genres: list[str] | None = None,
    ) -> Game:
        """Create a new game entry.

        Raises:
            ValueError: If a game with the same *slug* already exists.
        """
        existing = await self._game_repo.get_by_slug(slug)
        if existing is not None:
            raise ValueError(f"Game with slug '{slug}' already exists")

        return await self._game_repo.create(
            slug=slug,
            title=title,
            metadata_source=metadata_source,
            igdb_id=igdb_id,
            summary=summary,
            cover_url=cover_url,
            first_release_date=first_release_date,
            genres=genres,
        )

    async def update_game(self, game_public_id: UUID, **fields: object) -> Game:
        """Update a game's fields.

        Raises:
            ValueError: If the game is not found.
        """
        game = await self._game_repo.get_by_public_id(game_public_id)
        if game is None:
            raise ValueError("Game not found")
        return await self._game_repo.update(game, **fields)

    async def list_genres(self) -> list[str]:
        """Return all distinct genre names from the games catalog."""
        return await self._game_repo.distinct_genres()

    async def search_games(self, query: str, limit: int = 20) -> list[Game]:
        """Search games by title."""
        return await self._game_repo.search(query, limit=limit)

    # ------------------------------------------------------------------
    # Platforms
    # ------------------------------------------------------------------
    async def list_platforms(self) -> list[Platform]:
        """Return all available platforms."""
        return await self._platform_repo.list_all()

    # ------------------------------------------------------------------
    # Library entries
    # ------------------------------------------------------------------
    async def add_to_library(
        self,
        user_id: int,
        game_public_id: UUID,
        platform_id: int,
        status: str = "backlog",
        notes: str | None = None,
        acquired_at: date | None = None,
    ) -> LibraryEntry:
        """Add a game to the user's library.

        Raises:
            ValueError: If the game or platform does not exist, or the entry
                is a duplicate.
        """
        game = await self._game_repo.get_by_public_id(game_public_id)
        if game is None:
            raise ValueError("Game not found")

        platform = await self._platform_repo.get_by_id(platform_id)
        if platform is None:
            raise ValueError("Platform not found")

        if await self._library_repo.exists(user_id, game.id, platform_id):
            raise ValueError("Library entry already exists for this game and platform")

        entry = await self._library_repo.create(
            user_id=user_id,
            game_id=game.id,
            platform_id=platform_id,
            status=status,
            notes=notes,
            acquired_at=acquired_at,
        )
        # Attach resolved relationships so callers can serialize immediately.
        entry.game = game
        entry.platform = platform
        return entry

    async def list_library(
        self,
        user_id: int,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[LibraryEntry], int]:
        """Return the user's library entries along with the total count."""
        entries = await self._library_repo.list_for_user(
            user_id, status=status, limit=limit, offset=offset
        )
        total = await self._library_repo.count_for_user(user_id, status=status)
        return entries, total

    async def update_entry(
        self,
        user_id: int,
        entry_public_id: UUID,
        **fields: object,
    ) -> LibraryEntry:
        """Update a library entry, validating ownership.

        Raises:
            ValueError: If the entry is not found or not owned by the user.
        """
        entry = await self._library_repo.get_by_public_id(entry_public_id, user_id)
        if entry is None:
            raise ValueError("Library entry not found")

        return await self._library_repo.update(entry, **fields)

    async def delete_entry(self, user_id: int, entry_public_id: UUID) -> None:
        """Delete a library entry, validating ownership.

        Raises:
            ValueError: If the entry is not found or not owned by the user.
        """
        entry = await self._library_repo.get_by_public_id(entry_public_id, user_id)
        if entry is None:
            raise ValueError("Library entry not found")

        await self._library_repo.delete(entry)
