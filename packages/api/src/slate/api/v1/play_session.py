"""PlaySession API endpoints: start, active, wrap_up, end, regenerate, list."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from slate.api.v1._cost_guard import cost_guard
from slate.api.v1._rate_limit import rate_limit
from slate.config import settings
from slate.core.play_session.schemas import (
    PlaySessionEndRequest,
    PlaySessionListItem,
    PlaySessionListResponse,
    PlaySessionResponse,
    PlaySessionStartRequest,
    PlaySessionWrapUpRequest,
    RecapPreviewRequest,
    RecapPreviewResponse,
    RegenerateRecapRequest,
    RetroactiveWrapUpRequest,
)
from slate.deps import CurrentUserDep, RequireVerifiedUserDep
from slate.deps.play_session import PlaySessionServiceDep

router = APIRouter(prefix="/v1/play-sessions", tags=["play_sessions"])

# Per-user limiter shared by the LLM-heavy recap routes (preview / deep
# recap / regenerate). Each call fans out to several model + web-research
# requests, so this is the most expensive surface to flood.
_recap_rate_limit = Depends(
    rate_limit(
        "play_session_recap",
        settings.rate_limit_play_session_recap_per_minute,
        60,
        by="user",
        fail_closed=True,
    )
)

# Aggregate $ cost kill-switch for the LLM-bearing play_session routes.
_play_session_cost_guard = Depends(cost_guard("play_session"))

# Wrap-up enqueues a background LLM extraction, so it must consume a cost permit +
# be throttled like the other play_session write surfaces (its own bucket).
_wrap_up_rate_limit = Depends(
    rate_limit(
        "play_session_wrap_up",
        settings.rate_limit_play_session_recap_per_minute,
        60,
        by="user",
        fail_closed=True,
    )
)


# ---------------------------------------------------------------------------
# Start a play_session
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=PlaySessionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_recap_rate_limit, _play_session_cost_guard],
)
async def start_play_session(
    body: PlaySessionStartRequest,
    current_user: RequireVerifiedUserDep,
    play_session_service: PlaySessionServiceDep,
) -> PlaySessionResponse:
    """Start a new play_session for a library entry.

    If ``recap_text`` is provided (from a prior preview call), the LLM
    recap generation step is skipped. Returns 409 if the user already
    has an active play_session.
    """
    play_session = await play_session_service.start_play_session(
        user_id=current_user.id,
        library_entry_public_id=body.library_entry_public_id,
        recap_text=body.recap_text,
        mode=body.mode,
        skip_recap=body.skip_recap,
    )
    return PlaySessionResponse.model_validate(play_session)


# ---------------------------------------------------------------------------
# Preview recap (before starting a play_session)
# ---------------------------------------------------------------------------


@router.post(
    "/preview-recap",
    response_model=RecapPreviewResponse,
    dependencies=[_recap_rate_limit, _play_session_cost_guard],
)
async def preview_recap(
    body: RecapPreviewRequest,
    current_user: RequireVerifiedUserDep,
    play_session_service: PlaySessionServiceDep,
) -> RecapPreviewResponse:
    """Generate a recap preview without creating a play_session.

    Returns the recap text and last session context so the user can
    review before committing to a play_session.
    """
    result = await play_session_service.preview_recap(
        user_id=current_user.id,
        library_entry_public_id=body.library_entry_public_id,
        position_override=body.position_override,
        mode=body.mode,
    )
    return RecapPreviewResponse.model_validate(result)


# ---------------------------------------------------------------------------
# Retroactive wrap_up (unregistered play session)
# ---------------------------------------------------------------------------


@router.post(
    "/retroactive-wrap-up",
    response_model=RecapPreviewResponse,
    dependencies=[_recap_rate_limit, _play_session_cost_guard],
)
async def submit_retroactive_wrap_up(
    body: RetroactiveWrapUpRequest,
    current_user: RequireVerifiedUserDep,
    play_session_service: PlaySessionServiceDep,
) -> RecapPreviewResponse:
    """Record a wrap_up for a play session that wasn't tracked.

    Creates a pre-ended retroactive play_session, extracts state, and returns
    an updated recap preview that includes the new data.
    """
    result = await play_session_service.submit_retroactive_wrap_up(
        user_id=current_user.id,
        library_entry_public_id=body.library_entry_public_id,
        wrap_up_text=body.wrap_up_text,
    )
    return RecapPreviewResponse.model_validate(result)


# ---------------------------------------------------------------------------
# Active play_session
# ---------------------------------------------------------------------------


@router.get("/active", response_model=PlaySessionResponse | None)
async def get_active_play_session(
    current_user: CurrentUserDep,
    play_session_service: PlaySessionServiceDep,
) -> PlaySessionResponse | None:
    """Return the user's currently active play_session, or null."""
    play_session = await play_session_service.get_active_play_session(current_user.id)
    if play_session is None:
        return None
    return PlaySessionResponse.model_validate(play_session)


# ---------------------------------------------------------------------------
# WrapUp
# ---------------------------------------------------------------------------


@router.patch(
    "/{public_id}/wrap-up",
    response_model=PlaySessionResponse,
    dependencies=[_wrap_up_rate_limit, _play_session_cost_guard],
)
async def submit_wrap_up(
    public_id: UUID,
    body: PlaySessionWrapUpRequest,
    current_user: CurrentUserDep,
    play_session_service: PlaySessionServiceDep,
) -> PlaySessionResponse:
    """Submit a wrap_up for a play_session, extracting state and ending it."""
    play_session = await play_session_service.submit_wrap_up(
        user_id=current_user.id,
        play_session_public_id=public_id,
        wrap_up_text=body.wrap_up_text,
    )
    return PlaySessionResponse.model_validate(play_session)


# ---------------------------------------------------------------------------
# End play_session (no wrap_up)
# ---------------------------------------------------------------------------


@router.post(
    "/{public_id}/end",
    response_model=PlaySessionResponse,
)
async def end_play_session(
    public_id: UUID,
    body: PlaySessionEndRequest,
    current_user: CurrentUserDep,
    play_session_service: PlaySessionServiceDep,
) -> PlaySessionResponse:
    """End a play_session without a wrap_up."""
    play_session = await play_session_service.end_play_session(
        user_id=current_user.id,
        play_session_public_id=public_id,
        ended_via=body.ended_via,
    )
    return PlaySessionResponse.model_validate(play_session)


# ---------------------------------------------------------------------------
# Regenerate recap
# ---------------------------------------------------------------------------


@router.post(
    "/{public_id}/recap/regenerate",
    response_model=PlaySessionResponse,
    dependencies=[_recap_rate_limit, _play_session_cost_guard],
)
async def regenerate_recap(
    public_id: UUID,
    current_user: RequireVerifiedUserDep,
    play_session_service: PlaySessionServiceDep,
    body: RegenerateRecapRequest | None = None,
) -> PlaySessionResponse:
    """Regenerate the recap for an active play_session.

    Optionally accepts a ``current_position`` field: the player's corrected
    in-game position, used when the previous session context is outdated.
    """
    position_override = body.current_position if body else None
    play_session = await play_session_service.regenerate_recap(
        user_id=current_user.id,
        play_session_public_id=public_id,
        position_override=position_override,
    )
    return PlaySessionResponse.model_validate(play_session)


# ---------------------------------------------------------------------------
# PlaySession listing and detail
# ---------------------------------------------------------------------------


@router.get("", response_model=PlaySessionListResponse)
async def list_play_sessions(
    current_user: CurrentUserDep,
    play_session_service: PlaySessionServiceDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PlaySessionListResponse:
    """List the current user's play_sessions."""
    play_sessions, total = await play_session_service.list_play_sessions(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )
    return PlaySessionListResponse(
        items=[PlaySessionListItem.model_validate(m) for m in play_sessions],
        total=total,
    )


@router.get("/{public_id}", response_model=PlaySessionResponse)
async def get_play_session(
    public_id: UUID,
    current_user: CurrentUserDep,
    play_session_service: PlaySessionServiceDep,
) -> PlaySessionResponse:
    """Get a single play_session with its details."""
    play_session = await play_session_service.get_play_session(current_user.id, public_id)
    return PlaySessionResponse.model_validate(play_session)
