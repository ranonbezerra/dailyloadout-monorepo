"""Loadout API endpoints: create, accept, reject, list."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from dailyloadout.api.v1._cost_guard import cost_guard
from dailyloadout.api.v1._rate_limit import rate_limit
from dailyloadout.config import settings
from dailyloadout.core.loadout.schemas import (
    LoadoutAcceptRequest,
    LoadoutCreateRequest,
    LoadoutListItem,
    LoadoutListResponse,
    LoadoutResponse,
    LoadoutStartRequest,
)
from dailyloadout.deps import CurrentUserDep, RequireVerifiedUserDep
from dailyloadout.deps.loadout import LoadoutServiceDep

router = APIRouter(prefix="/v1/loadouts", tags=["loadouts"])

# Per-user limiter on the LLM-pick routes (create + one-tap start). Each call
# runs a smart-model pick over the eligible library, so it's the expensive
# loadout surface worth bounding per account.
_loadout_create_rate_limit = Depends(
    rate_limit(
        "loadout_create",
        settings.rate_limit_loadout_create_per_minute,
        60,
        by="user",
        fail_closed=True,
    )
)

# Aggregate $ cost kill-switch for the LLM-pick loadout routes.
_loadout_cost_guard = Depends(cost_guard("loadout"))


# ---------------------------------------------------------------------------
# Create loadout
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=list[LoadoutResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[_loadout_create_rate_limit, _loadout_cost_guard],
)
async def create_loadout(
    body: LoadoutCreateRequest,
    current_user: RequireVerifiedUserDep,
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
# Start: AI-pick a game and start a mission in one step
# ---------------------------------------------------------------------------


@router.post(
    "/start",
    response_model=LoadoutResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_loadout_create_rate_limit, _loadout_cost_guard],
)
async def start_loadout(
    body: LoadoutStartRequest,
    current_user: RequireVerifiedUserDep,
    loadout_service: LoadoutServiceDep,
) -> LoadoutResponse:
    """AI-pick a game and immediately start a mission for it (one tap).

    Optionally include a pre-generated ``briefing_text`` to start briefed.
    Returns 422 if no eligible games, 409 if a mission is already active.
    """
    loadout = await loadout_service.create_and_start(
        user_id=current_user.id,
        mood=body.mood,
        available_minutes=body.available_minutes,
        mental_energy=body.mental_energy,
        context=body.context,
        briefing_text=body.briefing_text,
    )
    return LoadoutResponse.model_validate(loadout)


# ---------------------------------------------------------------------------
# Accept loadout → creates mission
# ---------------------------------------------------------------------------


@router.post("/{public_id}/accept", response_model=LoadoutResponse)
async def accept_loadout(
    public_id: UUID,
    current_user: CurrentUserDep,
    loadout_service: LoadoutServiceDep,
    body: LoadoutAcceptRequest | None = None,
) -> LoadoutResponse:
    """Accept a loadout suggestion and start a mission for the chosen game.

    Optionally include a pre-generated ``briefing_text`` to start with a
    briefing (the briefing stage is skippable — omit the body to start without).
    """
    loadout = await loadout_service.accept_loadout(
        user_id=current_user.id,
        loadout_public_id=public_id,
        briefing_text=body.briefing_text if body else None,
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
