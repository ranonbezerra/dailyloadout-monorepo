"""Pick API endpoints: create, accept, reject, list."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from slate.api.v1._cost_guard import cost_guard
from slate.api.v1._rate_limit import rate_limit
from slate.config import settings
from slate.core.pick.schemas import (
    PickAcceptRequest,
    PickCreateRequest,
    PickListItem,
    PickListResponse,
    PickResponse,
    PickStartRequest,
)
from slate.deps import CurrentUserDep, RequireVerifiedUserDep
from slate.deps.pick import PickServiceDep

router = APIRouter(prefix="/v1/picks", tags=["picks"])

# Per-user limiter on the LLM-selection routes (create + one-tap start). Each call
# runs a smart-model selection over the eligible library, so it's the expensive
# pick surface worth bounding per account.
_pick_create_rate_limit = Depends(
    rate_limit(
        "pick_create",
        settings.rate_limit_pick_create_per_minute,
        60,
        by="user",
        fail_closed=True,
    )
)

# Aggregate $ cost kill-switch for the LLM-selection pick routes.
_pick_cost_guard = Depends(cost_guard("pick"))


# ---------------------------------------------------------------------------
# Create pick
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=list[PickResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[_pick_create_rate_limit, _pick_cost_guard],
)
async def create_pick(
    body: PickCreateRequest,
    current_user: RequireVerifiedUserDep,
    pick_service: PickServiceDep,
) -> list[PickResponse]:
    """Create daily Pick suggestions (1-3).

    Picks games from the user's eligible library entries based on mood,
    available time, and mental energy.  Returns 422 if no eligible games
    or the LLM cannot pick a valid game.
    """
    picks = await pick_service.create_picks(
        user_id=current_user.id,
        mood=body.mood,
        available_minutes=body.available_minutes,
        mental_energy=body.mental_energy,
        context=body.context,
        count=body.count,
    )
    return [PickResponse.model_validate(p) for p in picks]


# ---------------------------------------------------------------------------
# Start: AI-pick a game and start a play_session in one step
# ---------------------------------------------------------------------------


@router.post(
    "/start",
    response_model=PickResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_pick_create_rate_limit, _pick_cost_guard],
)
async def start_pick(
    body: PickStartRequest,
    current_user: RequireVerifiedUserDep,
    pick_service: PickServiceDep,
) -> PickResponse:
    """AI-pick a game and immediately start a play_session for it (one tap).

    Optionally include a pre-generated ``recap_text`` to start with a recap ready.
    Returns 422 if no eligible games, 409 if a play_session is already active.
    """
    pick = await pick_service.create_and_start(
        user_id=current_user.id,
        mood=body.mood,
        available_minutes=body.available_minutes,
        mental_energy=body.mental_energy,
        context=body.context,
        recap_text=body.recap_text,
    )
    return PickResponse.model_validate(pick)


# ---------------------------------------------------------------------------
# Accept pick → creates play_session
# ---------------------------------------------------------------------------


@router.post("/{public_id}/accept", response_model=PickResponse)
async def accept_pick(
    public_id: UUID,
    current_user: CurrentUserDep,
    pick_service: PickServiceDep,
    body: PickAcceptRequest | None = None,
) -> PickResponse:
    """Accept a Pick suggestion and start a play_session for the chosen game.

    Optionally include a pre-generated ``recap_text`` to start with a
    recap (the recap stage is skippable — omit the body to start without).
    """
    pick = await pick_service.accept_pick(
        user_id=current_user.id,
        pick_public_id=public_id,
        recap_text=body.recap_text if body else None,
    )
    return PickResponse.model_validate(pick)


# ---------------------------------------------------------------------------
# Reject pick
# ---------------------------------------------------------------------------


@router.post("/{public_id}/reject", response_model=PickResponse)
async def reject_pick(
    public_id: UUID,
    current_user: CurrentUserDep,
    pick_service: PickServiceDep,
) -> PickResponse:
    """Reject a Pick suggestion."""
    pick = await pick_service.reject_pick(
        user_id=current_user.id,
        pick_public_id=public_id,
    )
    return PickResponse.model_validate(pick)


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------


@router.get("", response_model=PickListResponse)
async def list_picks(
    current_user: CurrentUserDep,
    pick_service: PickServiceDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PickListResponse:
    """List the current user's pick history."""
    picks, total = await pick_service.list_picks(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )
    return PickListResponse(
        items=[PickListItem.model_validate(p) for p in picks],
        total=total,
    )


@router.get("/latest", response_model=PickResponse | None)
async def get_latest_pick(
    current_user: CurrentUserDep,
    pick_service: PickServiceDep,
) -> PickResponse | None:
    """Return the latest pending Pick, or null."""
    pick = await pick_service.get_latest_pending(current_user.id)
    if pick is None:
        return None
    return PickResponse.model_validate(pick)
