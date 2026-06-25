"""Library API endpoints: games, platforms, library CRUD."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from dailyloadout.core.library.schemas import (
    GameCreate,
    GameResponse,
    GameUpdate,
    LibraryEntryCreate,
    LibraryEntryResponse,
    LibraryEntryUpdate,
    LibraryListResponse,
    PlatformResponse,
)
from dailyloadout.deps import CurrentUserDep, LibraryServiceDep

router = APIRouter(prefix="/v1", tags=["library"])


# ---------------------------------------------------------------------------
# Games
# ---------------------------------------------------------------------------


@router.post(
    "/games",
    response_model=GameResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_game(
    body: GameCreate,
    current_user: CurrentUserDep,
    library_service: LibraryServiceDep,
) -> GameResponse:
    """Create a game manually."""
    try:
        game = await library_service.create_game(
            slug=body.slug,
            title=body.title,
            metadata_source=body.metadata_source,
            summary=body.summary,
            cover_url=body.cover_url,
            first_release_date=body.first_release_date,
            genres=body.genres,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return GameResponse.model_validate(game)


@router.patch("/games/{public_id}", response_model=GameResponse)
async def update_game(
    public_id: UUID,
    body: GameUpdate,
    current_user: CurrentUserDep,
    library_service: LibraryServiceDep,
) -> GameResponse:
    """Update a game's details (e.g. genres)."""
    update_fields = body.model_dump(exclude_unset=True)
    try:
        game = await library_service.update_game(
            game_public_id=public_id,
            **update_fields,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return GameResponse.model_validate(game)


@router.get("/games/genres", response_model=list[str])
async def list_genres(
    current_user: CurrentUserDep,
    library_service: LibraryServiceDep,
) -> list[str]:
    """Return all distinct genre names from the games catalog."""
    return await library_service.list_genres()


@router.get("/games/search", response_model=list[GameResponse])
async def search_games(
    current_user: CurrentUserDep,
    library_service: LibraryServiceDep,
    q: str = Query(min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[GameResponse]:
    """Fuzzy-search games by title."""
    games = await library_service.search_games(q, limit=limit)
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
    platforms = await library_service.list_platforms()
    return [PlatformResponse.model_validate(p) for p in platforms]


# ---------------------------------------------------------------------------
# Library entries
# ---------------------------------------------------------------------------


@router.get("/library", response_model=LibraryListResponse)
async def list_library(
    current_user: CurrentUserDep,
    library_service: LibraryServiceDep,
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> LibraryListResponse:
    """List the current user's library entries."""
    entries, total = await library_service.list_library(
        user_id=current_user.id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return LibraryListResponse(
        items=[LibraryEntryResponse.model_validate(e) for e in entries],
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
    response_model=LibraryEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_to_library(
    body: LibraryEntryCreate,
    current_user: CurrentUserDep,
    library_service: LibraryServiceDep,
) -> LibraryEntryResponse:
    """Add a game to the current user's library."""
    try:
        entry = await library_service.add_to_library(
            user_id=current_user.id,
            game_public_id=body.game_public_id,
            platform_id=body.platform_id,
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

    return LibraryEntryResponse.model_validate(entry)


@router.patch("/library/{public_id}", response_model=LibraryEntryResponse)
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
