"""Backoffice games/catalogue service (Epic 21, Phase 5).

Read + moderate the shared game catalogue: list/search with owner counts,
inspect a row, demote a poisoned shared row back to private (the
``demote_game.py`` primitive as a panel action), promote a vetted manual row,
and edit basic metadata. Every mutation is audited. Orchestrates repos only.
"""

from __future__ import annotations

from uuid import UUID

from dailyloadout.core.admin.schemas import (
    AdminGameDetail,
    AdminGameList,
    AdminGameSummary,
    GameEditRequest,
)
from dailyloadout.infrastructure.db.models import Game, User
from dailyloadout.infrastructure.db.repositories.admin import AdminAuditRepository
from dailyloadout.infrastructure.db.repositories.game import GameRepository
from dailyloadout.infrastructure.db.repositories.user import UserRepository

ACTION_DEMOTE = "game.demote"
ACTION_PROMOTE = "game.promote"
ACTION_EDIT = "game.edit"


class GameNotFoundError(Exception):
    """Raised when a backoffice action targets an unknown game public_id."""


def _source(game: Game) -> str:
    return "igdb" if game.igdb_id is not None else "manual"


class AdminGameService:
    """Catalogue moderation for the backoffice."""

    def __init__(
        self,
        game_repo: GameRepository,
        user_repo: UserRepository,
        audit_repo: AdminAuditRepository,
    ) -> None:
        self._games = game_repo
        self._users = user_repo
        self._audit = audit_repo

    async def list_games(
        self,
        *,
        query: str | None,
        is_shared: bool | None,
        source: str | None,
        limit: int,
        offset: int,
    ) -> AdminGameList:
        """Return a page of games (with owner counts) + catalogue tallies."""
        rows, total = await self._games.search_admin(
            query=query, is_shared=is_shared, source=source, limit=limit, offset=offset
        )
        cat_total, cat_igdb, cat_manual = await self._games.catalogue_counts()
        return AdminGameList(
            items=[_summary(game, owners) for game, owners in rows],
            total=total,
            limit=limit,
            offset=offset,
            catalogue_total=cat_total,
            catalogue_igdb=cat_igdb,
            catalogue_manual=cat_manual,
        )

    async def get_game(self, public_id: UUID) -> AdminGameDetail:
        """Return the full backoffice view of one game, or raise if unknown."""
        game = await self._require_game(public_id)
        return await self._detail(game)

    async def demote_game(self, actor: User, public_id: UUID) -> AdminGameDetail:
        """Demote a shared row back to private (removes it from the catalogue)."""
        game = await self._require_game(public_id)
        await self._games.update(game, is_shared=False)
        await self._audit.record(admin_user_id=actor.id, action=ACTION_DEMOTE, detail=game.slug)
        await self._games.refresh(game)
        return await self._detail(game)

    async def promote_game(self, actor: User, public_id: UUID) -> AdminGameDetail:
        """Promote a private manual row into the shared catalogue."""
        game = await self._require_game(public_id)
        await self._games.update(game, is_shared=True)
        await self._audit.record(admin_user_id=actor.id, action=ACTION_PROMOTE, detail=game.slug)
        await self._games.refresh(game)
        return await self._detail(game)

    async def edit_game(
        self, actor: User, public_id: UUID, edit: GameEditRequest
    ) -> AdminGameDetail:
        """Edit a game's title/summary (only provided fields change), audited."""
        game = await self._require_game(public_id)
        fields = edit.model_dump(exclude_unset=True, exclude_none=True)
        if fields:
            await self._games.update(game, **fields)
            await self._audit.record(
                admin_user_id=actor.id,
                action=ACTION_EDIT,
                detail=f"{game.slug}: {', '.join(sorted(fields))}",
            )
            await self._games.refresh(game)
        return await self._detail(game)

    # ── Internals ──
    async def _require_game(self, public_id: UUID) -> Game:
        game = await self._games.get_by_public_id(public_id)
        if game is None:
            raise GameNotFoundError
        return game

    async def _detail(self, game: Game) -> AdminGameDetail:
        owners = await self._games.owner_count(game.id)
        creator_email: str | None = None
        if game.created_by_user_id is not None:
            creator = await self._users.get_by_id(game.created_by_user_id)
            creator_email = creator.email if creator is not None else None
        return AdminGameDetail(
            public_id=game.public_id,
            slug=game.slug,
            title=game.title,
            igdb_id=game.igdb_id,
            source=_source(game),
            is_shared=game.is_shared,
            cover_url=game.cover_url,
            owner_count=owners,
            created_at=game.created_at,
            summary=game.summary,
            genres=game.genres,
            first_release_date=game.first_release_date,
            metadata_source=game.metadata_source,
            created_by_email=creator_email,
            updated_at=game.updated_at,
        )


def _summary(game: Game, owners: int) -> AdminGameSummary:
    return AdminGameSummary(
        public_id=game.public_id,
        slug=game.slug,
        title=game.title,
        igdb_id=game.igdb_id,
        source=_source(game),
        is_shared=game.is_shared,
        cover_url=game.cover_url,
        owner_count=owners,
        created_at=game.created_at,
    )
