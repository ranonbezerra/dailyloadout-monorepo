"""Backoffice missions moderation API (Epic 21, Phase 6).

Served under ``/internal/v1/missions`` — a separate module from ``admin.py`` to
keep each router file within the 300-line budget. Every route is admin-gated and
mutations are audited like the rest of the backoffice.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from dailyloadout.core.admin.missions_service import (
    MissionNotActiveError,
    MissionNotFoundError,
)
from dailyloadout.core.admin.schemas import AdminMissionDetail, AdminMissionList
from dailyloadout.deps.auth import AdminMissionServiceDep, AdminUserDep

router = APIRouter(prefix="/internal/v1", tags=["internal"])


@router.get("/missions", response_model=AdminMissionList)
async def list_missions(
    _admin: AdminUserDep,
    service: AdminMissionServiceDep,
    q: str | None = Query(default=None, description="Match the owner's email"),
    status_filter: str | None = Query(default=None, alias="status", pattern="^(active|ended)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AdminMissionList:
    """List/search missions across all users with per-status tallies (paginated)."""
    return await service.list_missions(query=q, status=status_filter, limit=limit, offset=offset)


@router.get("/missions/{public_id}", response_model=AdminMissionDetail)
async def get_mission(
    public_id: UUID,
    _admin: AdminUserDep,
    service: AdminMissionServiceDep,
) -> AdminMissionDetail:
    """Return the full backoffice view of a single mission."""
    try:
        return await service.get_mission(public_id)
    except MissionNotFoundError:
        raise _not_found() from None


@router.post("/missions/{public_id}/clamp", response_model=AdminMissionDetail)
async def clamp_mission(
    public_id: UUID,
    admin: AdminUserDep,
    service: AdminMissionServiceDep,
) -> AdminMissionDetail:
    """Force-end a stuck active mission now (409 if it already ended)."""
    try:
        return await service.clamp_mission(admin, public_id)
    except MissionNotFoundError:
        raise _not_found() from None
    except MissionNotActiveError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Mission has already ended.",
        ) from None


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission not found")
