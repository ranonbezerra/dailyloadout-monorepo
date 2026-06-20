"""Mission API endpoints: start, active, debrief, end, regenerate, list."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, status

from dailyloadout.core.mission.schemas import (
    BriefingPreviewRequest,
    BriefingPreviewResponse,
    MissionDebriefRequest,
    MissionEndRequest,
    MissionListItem,
    MissionListResponse,
    MissionResponse,
    MissionStartRequest,
    RegenerateBriefingRequest,
    RetroactiveDebriefRequest,
)
from dailyloadout.deps import CurrentUserDep
from dailyloadout.deps.mission import MissionServiceDep

router = APIRouter(prefix="/v1/missions", tags=["missions"])


# ---------------------------------------------------------------------------
# Start a mission
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=MissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_mission(
    body: MissionStartRequest,
    current_user: CurrentUserDep,
    mission_service: MissionServiceDep,
) -> MissionResponse:
    """Start a new mission for a library entry.

    If ``briefing_text`` is provided (from a prior preview call), the LLM
    briefing generation step is skipped. Returns 409 if the user already
    has an active mission.
    """
    mission = await mission_service.start_mission(
        user_id=current_user.id,
        library_entry_public_id=body.library_entry_public_id,
        briefing_text=body.briefing_text,
    )
    return MissionResponse.model_validate(mission)


# ---------------------------------------------------------------------------
# Preview briefing (before starting a mission)
# ---------------------------------------------------------------------------


@router.post(
    "/preview-briefing",
    response_model=BriefingPreviewResponse,
)
async def preview_briefing(
    body: BriefingPreviewRequest,
    current_user: CurrentUserDep,
    mission_service: MissionServiceDep,
) -> BriefingPreviewResponse:
    """Generate a briefing preview without creating a mission.

    Returns the briefing text and last session context so the user can
    review before committing to a mission.
    """
    result = await mission_service.preview_briefing(
        user_id=current_user.id,
        library_entry_public_id=body.library_entry_public_id,
        position_override=body.position_override,
    )
    return BriefingPreviewResponse.model_validate(result)


# ---------------------------------------------------------------------------
# Retroactive debrief (unregistered play session)
# ---------------------------------------------------------------------------


@router.post(
    "/retroactive-debrief",
    response_model=BriefingPreviewResponse,
)
async def submit_retroactive_debrief(
    body: RetroactiveDebriefRequest,
    current_user: CurrentUserDep,
    mission_service: MissionServiceDep,
) -> BriefingPreviewResponse:
    """Record a debrief for a play session that wasn't tracked.

    Creates a pre-ended retroactive mission, extracts state, and returns
    an updated briefing preview that includes the new data.
    """
    result = await mission_service.submit_retroactive_debrief(
        user_id=current_user.id,
        library_entry_public_id=body.library_entry_public_id,
        debrief_text=body.debrief_text,
    )
    return BriefingPreviewResponse.model_validate(result)


# ---------------------------------------------------------------------------
# Active mission
# ---------------------------------------------------------------------------


@router.get("/active", response_model=MissionResponse | None)
async def get_active_mission(
    current_user: CurrentUserDep,
    mission_service: MissionServiceDep,
) -> MissionResponse | None:
    """Return the user's currently active mission, or null."""
    mission = await mission_service.get_active_mission(current_user.id)
    if mission is None:
        return None
    return MissionResponse.model_validate(mission)


# ---------------------------------------------------------------------------
# Debrief
# ---------------------------------------------------------------------------


@router.patch(
    "/{public_id}/debrief",
    response_model=MissionResponse,
)
async def submit_debrief(
    public_id: UUID,
    body: MissionDebriefRequest,
    current_user: CurrentUserDep,
    mission_service: MissionServiceDep,
) -> MissionResponse:
    """Submit a debrief for a mission, extracting state and ending it."""
    mission = await mission_service.submit_debrief(
        user_id=current_user.id,
        mission_public_id=public_id,
        debrief_text=body.debrief_text,
    )
    return MissionResponse.model_validate(mission)


# ---------------------------------------------------------------------------
# End mission (no debrief)
# ---------------------------------------------------------------------------


@router.post(
    "/{public_id}/end",
    response_model=MissionResponse,
)
async def end_mission(
    public_id: UUID,
    body: MissionEndRequest,
    current_user: CurrentUserDep,
    mission_service: MissionServiceDep,
) -> MissionResponse:
    """End a mission without a debrief."""
    mission = await mission_service.end_mission(
        user_id=current_user.id,
        mission_public_id=public_id,
        ended_via=body.ended_via,
    )
    return MissionResponse.model_validate(mission)


# ---------------------------------------------------------------------------
# Regenerate briefing
# ---------------------------------------------------------------------------


@router.post(
    "/{public_id}/briefing/regenerate",
    response_model=MissionResponse,
)
async def regenerate_briefing(
    public_id: UUID,
    current_user: CurrentUserDep,
    mission_service: MissionServiceDep,
    body: RegenerateBriefingRequest | None = None,
) -> MissionResponse:
    """Regenerate the briefing for an active mission.

    Optionally accepts a ``current_position`` field: the player's corrected
    in-game position, used when the previous session context is outdated.
    """
    position_override = body.current_position if body else None
    mission = await mission_service.regenerate_briefing(
        user_id=current_user.id,
        mission_public_id=public_id,
        position_override=position_override,
    )
    return MissionResponse.model_validate(mission)


# ---------------------------------------------------------------------------
# Mission listing and detail
# ---------------------------------------------------------------------------


@router.get("", response_model=MissionListResponse)
async def list_missions(
    current_user: CurrentUserDep,
    mission_service: MissionServiceDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> MissionListResponse:
    """List the current user's missions."""
    missions, total = await mission_service.list_missions(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )
    return MissionListResponse(
        items=[MissionListItem.model_validate(m) for m in missions],
        total=total,
    )


@router.get("/{public_id}", response_model=MissionResponse)
async def get_mission(
    public_id: UUID,
    current_user: CurrentUserDep,
    mission_service: MissionServiceDep,
) -> MissionResponse:
    """Get a single mission with its details."""
    mission = await mission_service.get_mission(current_user.id, public_id)
    return MissionResponse.model_validate(mission)
