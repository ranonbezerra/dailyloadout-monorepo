"""Loadout API endpoints: create, accept, reject, list."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, status

from dailyloadout.core.loadout.schemas import (
    LoadoutCreateRequest,
    LoadoutListItem,
    LoadoutListResponse,
    LoadoutResponse,
)
from dailyloadout.deps import CurrentUserDep
from dailyloadout.deps.loadout import LoadoutServiceDep

router = APIRouter(prefix="/v1/loadouts", tags=["loadouts"])


# ---------------------------------------------------------------------------
# Create loadout
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=list[LoadoutResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_loadout(
    body: LoadoutCreateRequest,
    current_user: CurrentUserDep,
    loadout_service: LoadoutServiceDep,
) -> list[LoadoutResponse]:
    """Create daily loadout suggestions (1-3).

    Picks games from the user's eligible library entries based on mood,
    available time, and mental energy.  Returns 422 if no eligible games
    or the LLM cannot pick a valid game.
    """
    loadouts = await loadout_service.create_loadouts(
        user_id=current_user.id,
        mood=body.mood,
        available_minutes=body.available_minutes,
        mental_energy=body.mental_energy,
        context=body.context,
        count=body.count,
    )
    return [LoadoutResponse.model_validate(lo) for lo in loadouts]


# ---------------------------------------------------------------------------
# Accept loadout → creates mission
# ---------------------------------------------------------------------------


@router.post("/{public_id}/accept", response_model=LoadoutResponse)
async def accept_loadout(
    public_id: UUID,
    current_user: CurrentUserDep,
    loadout_service: LoadoutServiceDep,
) -> LoadoutResponse:
    """Accept a loadout suggestion and start a mission for the chosen game."""
    loadout = await loadout_service.accept_loadout(
        user_id=current_user.id,
        loadout_public_id=public_id,
    )
    return LoadoutResponse.model_validate(loadout)


# ---------------------------------------------------------------------------
# Reject loadout
# ---------------------------------------------------------------------------


@router.post("/{public_id}/reject", response_model=LoadoutResponse)
async def reject_loadout(
    public_id: UUID,
    current_user: CurrentUserDep,
    loadout_service: LoadoutServiceDep,
) -> LoadoutResponse:
    """Reject a loadout suggestion."""
    loadout = await loadout_service.reject_loadout(
        user_id=current_user.id,
        loadout_public_id=public_id,
    )
    return LoadoutResponse.model_validate(loadout)


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------


@router.get("", response_model=LoadoutListResponse)
async def list_loadouts(
    current_user: CurrentUserDep,
    loadout_service: LoadoutServiceDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> LoadoutListResponse:
    """List the current user's loadout history."""
    loadouts, total = await loadout_service.list_loadouts(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )
    return LoadoutListResponse(
        items=[LoadoutListItem.model_validate(lo) for lo in loadouts],
        total=total,
    )


@router.get("/latest", response_model=LoadoutResponse | None)
async def get_latest_loadout(
    current_user: CurrentUserDep,
    loadout_service: LoadoutServiceDep,
) -> LoadoutResponse | None:
    """Return the latest pending loadout, or null."""
    loadout = await loadout_service.get_latest_pending(current_user.id)
    if loadout is None:
        return None
    return LoadoutResponse.model_validate(loadout)
