"""Library service: game management, library CRUD operations."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from dailyloadout.core.cache.invalidation import invalidate_user_stats
from dailyloadout.core.library.backfill import enrich_in_place, reconcile_manual_title
from dailyloadout.core.library.schemas import (
    GameResponse,
    LibraryGameGroup,
    LibraryPlatformState,
)
from dailyloadout.infrastructure.cache.base import AbstractCache, NullCache
from dailyloadout.infrastructure.cache.keys import NS_REF, reference_key
from dailyloadout.infrastructure.cache.layer import cached_call
from dailyloadout.infrastructure.db.models import Game, LibraryEntry, Platform
from dailyloadout.infrastructure.db.repositories.game import GameRepository
from dailyloadout.infrastructure.db.repositories.library import LibraryRepository
from dailyloadout.infrastructure.db.repositories.platform import PlatformRepository
from dailyloadout.infrastructure.igdb.base import IGDBSearchClient


class LibraryService:
    """Orchestrates game catalog and user library operations.

    Writes invalidate stats ambiently (see ``invalidate_user_stats``); the
    *cache* here is for the read side only — the global genre list (Epic 18
    reference tier). Mirrors ``StatsService``: caching reads are injected, busts
    are ambient.
    """

    def __init__(
        self,
        game_repo: GameRepository,
        library_repo: LibraryRepository,
        platform_repo: PlatformRepository,
        cache: AbstractCache | None = None,
        reference_ttl_seconds: int = 3600,
        igdb_client: IGDBSearchClient | None = None,
        match_min_score: float = 0.6,
    ) -> None:
        self._game_repo = game_repo
        self._library_repo = library_repo
        self._platform_repo = platform_repo
        self._cache = cache or NullCache()
        self._reference_ttl = reference_ttl_seconds
        self._igdb_client = igdb_client
        self._match_min_score = match_min_score

    # ------------------------------------------------------------------
    # Games
    # ------------------------------------------------------------------
    async def create_game(
        self,
        *,
        user_id: int,
        slug: str,
        title: str,
        summary: str | None = None,
        cover_url: str | None = None,
        first_release_date: date | None = None,
        genres: list[str] | None = None,
    ) -> Game:
        """Resolve *(slug, title)* to a shared global game, DB-first.

        ``Game`` rows are global/shared; the server — not the client — decides
        ``metadata_source``. Resolution order:

        1. If we already hold a row for *slug* (any creator), return it (enriching
           it in place from IGDB first if it lacks IGDB metadata). Idempotent —
           the next user relates to the existing row instead of duplicating it.
        2. Else if IGDB confidently matches *title*, reuse/create a canonical
           GLOBAL row.
        3. Else create a manual GLOBAL row, attributed to *user_id*.
        """
        existing = await self._game_repo.get_by_slug(slug)
        if existing is not None:
            if existing.igdb_id is None:
                await enrich_in_place(
                    existing,
                    igdb_client=self._igdb_client,
                    game_repo=self._game_repo,
                    min_score=self._match_min_score,
                )
            return existing

        reconciled = await reconcile_manual_title(
            title,
            igdb_client=self._igdb_client,
            game_repo=self._game_repo,
            min_score=self._match_min_score,
        )
        if reconciled is not None:
            return reconciled

        return await self._game_repo.create(
            slug=slug,
            title=title,
            metadata_source="manual",
            igdb_id=None,
            summary=summary,
            cover_url=cover_url,
            first_release_date=first_release_date,
            genres=genres,
            created_by_user_id=user_id,
        )

    async def list_genres(self) -> list[str]:
        """Return all distinct genre names from the games catalog.

        Global, tiny, and rarely-changing — cached with a TTL (no event bust;
        new genres surface within the TTL).
        """
        return await cached_call(
            cache=self._cache,
            key=reference_key("genres"),
            ttl_seconds=self._reference_ttl,
            namespace=NS_REF,
            compute=self._game_repo.distinct_genres,
        )

    async def search_games(self, query: str, limit: int = 20) -> list[Game]:
        """Search games by title across the shared global catalogue."""
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
        platform_ids: list[int],
        status: str = "backlog",
        notes: str | None = None,
        acquired_at: date | None = None,
    ) -> LibraryGameGroup:
        """Add a game to the user's library on one or more platforms.

        Creates one per-platform entry for each requested platform, SKIPPING any
        platform the user already owns for this game (idempotent re-add). Returns
        the resulting grouped row for the game, including all its platform states.

        Raises:
            ValueError: If the game or any requested platform does not exist.
        """
        game = await self._game_repo.get_by_public_id(game_public_id)
        if game is None:
            raise ValueError("Game not found")

        for platform_id in platform_ids:
            platform = await self._platform_repo.get_by_id(platform_id)
            if platform is None:
                raise ValueError("Platform not found")

            if await self._library_repo.exists(user_id, game.id, platform_id):
                # Idempotent re-add: skip platforms already owned for this game.
                continue

            await self._library_repo.create(
                user_id=user_id,
                game_id=game.id,
                platform_id=platform_id,
                status=status,
                notes=notes,
                acquired_at=acquired_at,
            )

        await invalidate_user_stats(user_id)

        entries = await self._library_repo.list_for_user_game(user_id, game.id)
        return self._group_entries(entries)[0]

    async def list_library(
        self,
        user_id: int,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[LibraryGameGroup], int]:
        """Return the user's library grouped by game, with the distinct-game total.

        Entries are fetched for one page of games (game-level pagination) and
        grouped on the backend into :class:`LibraryGameGroup`s. When *status* is
        given, only matching platform states are included, and *total* counts
        only games that have at least one matching entry.
        """
        entries = await self._library_repo.list_grouped_for_user(
            user_id, status=status, limit=limit, offset=offset
        )
        total = await self._library_repo.count_games_for_user(user_id, status=status)
        return self._group_entries(entries), total

    @staticmethod
    def _group_entries(entries: list[LibraryEntry]) -> list[LibraryGameGroup]:
        """Group pre-ordered per-platform *entries* into per-game groups.

        Relies on the repository having ordered entries so a game's rows are
        contiguous; preserves that game order and the per-platform order.
        """
        groups: list[LibraryGameGroup] = []
        index: dict[int, LibraryGameGroup] = {}
        for entry in entries:
            group = index.get(entry.game_id)
            if group is None:
                group = LibraryGameGroup(
                    game=GameResponse.model_validate(entry.game),
                    platforms=[],
                )
                index[entry.game_id] = group
                groups.append(group)
            group.platforms.append(LibraryPlatformState.model_validate(entry))
        return groups

    async def get_entry(self, user_id: int, entry_public_id: UUID) -> LibraryEntry:
        """Return a single library entry owned by the user.

        Raises:
            ValueError: If the entry is not found or not owned by the user.
        """
        entry = await self._library_repo.get_by_public_id(entry_public_id, user_id)
        if entry is None:
            raise ValueError("Library entry not found")
        return entry

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

        updated = await self._library_repo.update(entry, **fields)
        await invalidate_user_stats(user_id)
        return updated

    async def delete_entry(self, user_id: int, entry_public_id: UUID) -> None:
        """Delete a library entry, validating ownership.

        Raises:
            ValueError: If the entry is not found or not owned by the user.
        """
        entry = await self._library_repo.get_by_public_id(entry_public_id, user_id)
        if entry is None:
            raise ValueError("Library entry not found")

        await self._library_repo.delete(entry)
        await invalidate_user_stats(user_id)
