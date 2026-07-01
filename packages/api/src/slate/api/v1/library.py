"""Library API endpoints: games, platforms, library CRUD."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from slate.api.v1._cost_guard import cost_guard
from slate.api.v1._rate_limit import rate_limit
from slate.config import settings
from slate.core.library.schemas import (
    GameCreate,
    GameResponse,
    LibraryEntryCreate,
    LibraryEntryResponse,
    LibraryEntryUpdate,
    LibraryGameGroup,
    LibraryGroupedResponse,
    PlatformResponse,
)
from slate.deps import CurrentUserDep, LibraryServiceDep, RequireVerifiedUserDep

router = APIRouter(prefix="/v1", tags=["library"])

# Per-user limiter + aggregate cost guard on the LLM/IGDB game-resolve route.
# fail_closed: losing the limiter on a cost-bearing route is unacceptable.
_game_create_rate_limit = Depends(
    rate_limit(
        "game_create",
        settings.rate_limit_game_create_per_minute,
        60,
        by="user",
        fail_closed=True,
    )
)
_game_create_cost_guard = Depends(cost_guard("game_create"))

# Generous per-user limiter for cheap library CRUD writes (backstop, not cost).
_library_write_rate_limit = Depends(
    rate_limit("library_write", settings.rate_limit_library_write_per_minute, 60, by="user")
)

# Generous per-user limiter for read-only catalogue endpoints (anti-scraping).
_read_rate_limit = Depends(
    rate_limit("library_read", settings.rate_limit_read_per_minute, 60, by="user")
)


# ---------------------------------------------------------------------------
# Games
# ---------------------------------------------------------------------------


@router.post(
    "/games",
    response_model=GameResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_game_create_rate_limit, _game_create_cost_guard],
)
async def create_game(
    body: GameCreate,
    current_user: RequireVerifiedUserDep,
    library_service: LibraryServiceDep,
) -> GameResponse:
    """Create or resolve a game (DB-first, IGDB enrichment on the fly).

    Idempotent: resolving an existing global row or the caller's own manual game
    returns it rather than conflicting.
    """
    game = await library_service.create_game(
        user_id=current_user.id,
        slug=body.slug,
        title=body.title,
        summary=body.summary,
        cover_url=body.cover_url,
        first_release_date=body.first_release_date,
        genres=body.genres,
    )
    return GameResponse.model_validate(game)


@router.get("/games/genres", response_model=list[str], dependencies=[_read_rate_limit])
async def list_genres(
    current_user: CurrentUserDep,
    library_service: LibraryServiceDep,
) -> list[str]:
    """Return all distinct genre names from the games catalog."""
    return await library_service.list_genres(user_id=current_user.id)


@router.get(
    "/games/search",
    response_model=list[GameResponse],
    dependencies=[_read_rate_limit],
)
async def search_games(
    current_user: CurrentUserDep,
    library_service: LibraryServiceDep,
    q: str = Query(min_length=3),
    limit: int = Query(default=20, ge=1, le=25),
) -> list[GameResponse]:
    """Fuzzy-search games by title."""
    games = await library_service.search_games(q, user_id=current_user.id, limit=limit)
    return [GameResponse.model_validate(g) for g in games]


# ---------------------------------------------------------------------------
# Platforms
# ---------------------------------------------------------------------------


@router.get("/platforms", response_model=list[PlatformResponse])
async def list_platforms(
    current_user: CurrentUserDep,
    library_service: LibraryServiceDep,
) -> list[PlatformResponse]:
    """List all available platforms."""
    return await library_service.list_platforms()


# ---------------------------------------------------------------------------
# Library entries
# ---------------------------------------------------------------------------


@router.get("/library", response_model=LibraryGroupedResponse)
async def list_library(
    current_user: CurrentUserDep,
    library_service: LibraryServiceDep,
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> LibraryGroupedResponse:
    """List the current user's library grouped by game.

    A game owned on multiple platforms appears as ONE item with its per-platform
    states nested. ``limit`` / ``offset`` page games; ``total`` is the number of
    distinct games.
    """
    groups, total = await library_service.list_library(
        user_id=current_user.id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return LibraryGroupedResponse(
        items=groups,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/library/{public_id}", response_model=LibraryEntryResponse)
async def get_library_entry(
    public_id: UUID,
    current_user: CurrentUserDep,
    library_service: LibraryServiceDep,
) -> LibraryEntryResponse:
    """Return a single library entry owned by the current user."""
    try:
        entry = await library_service.get_entry(current_user.id, public_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return LibraryEntryResponse.model_validate(entry)


@router.post(
    "/library",
    response_model=LibraryGameGroup,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_library_write_rate_limit],
)
async def add_to_library(
    body: LibraryEntryCreate,
    current_user: CurrentUserDep,
    library_service: LibraryServiceDep,
) -> LibraryGameGroup:
    """Add a game to the current user's library on one or more platforms.

    Returns the resulting grouped row for the game; re-adding a platform the user
    already owns is idempotent (skipped, no error).
    """
    try:
        return await library_service.add_to_library(
            user_id=current_user.id,
            game_public_id=body.game_public_id,
            platform_ids=body.platform_ids,
            status=body.status,
            notes=body.notes,
            acquired_at=body.acquired_at,
        )
    except ValueError as exc:
        detail = str(exc)
        if "not found" in detail.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=detail,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        ) from exc


@router.patch(
    "/library/{public_id}",
    response_model=LibraryEntryResponse,
    dependencies=[_library_write_rate_limit],
)
async def update_library_entry(
    public_id: UUID,
    body: LibraryEntryUpdate,
    current_user: CurrentUserDep,
    library_service: LibraryServiceDep,
) -> LibraryEntryResponse:
    """Update a library entry owned by the current user."""
    update_fields = body.model_dump(exclude_unset=True)
    try:
        entry = await library_service.update_entry(
            user_id=current_user.id,
            entry_public_id=public_id,
            **update_fields,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return LibraryEntryResponse.model_validate(entry)


@router.delete(
    "/library/{public_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_library_write_rate_limit],
)
async def delete_library_entry(
    public_id: UUID,
    current_user: CurrentUserDep,
    library_service: LibraryServiceDep,
) -> None:
    """Delete a library entry owned by the current user."""
    try:
        await library_service.delete_entry(
            user_id=current_user.id,
            entry_public_id=public_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
