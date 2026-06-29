"""Backoffice play_sessions moderation API (Epic 21, Phase 6).

Served under ``/internal/v1/play-sessions`` — a separate module from ``admin.py`` to
keep each router file within the 300-line budget. Every route is admin-gated and
mutations are audited like the rest of the backoffice.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from slate.core.admin.play_sessions_service import (
    PlaySessionNotActiveError,
    PlaySessionNotFoundError,
)
from slate.core.admin.schemas import AdminPlaySessionDetail, AdminPlaySessionList
from slate.deps.admin import AdminPlaySessionServiceDep
from slate.deps.auth import AdminUserDep

router = APIRouter(prefix="/internal/v1", tags=["internal"])


@router.get("/play-sessions", response_model=AdminPlaySessionList)
async def list_play_sessions(
    _admin: AdminUserDep,
    service: AdminPlaySessionServiceDep,
    q: str | None = Query(default=None, description="Match the owner's email"),
    status_filter: str | None = Query(default=None, alias="status", pattern="^(active|ended)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AdminPlaySessionList:
    """List/search play_sessions across all users with per-status tallies (paginated)."""
    return await service.list_play_sessions(
        query=q, status=status_filter, limit=limit, offset=offset
    )


@router.get("/play-sessions/{public_id}", response_model=AdminPlaySessionDetail)
async def get_play_session(
    public_id: UUID,
    _admin: AdminUserDep,
    service: AdminPlaySessionServiceDep,
) -> AdminPlaySessionDetail:
    """Return the full backoffice view of a single play_session."""
    try:
        return await service.get_play_session(public_id)
    except PlaySessionNotFoundError:
        raise _not_found() from None


@router.post("/play-sessions/{public_id}/clamp", response_model=AdminPlaySessionDetail)
async def clamp_play_session(
    public_id: UUID,
    admin: AdminUserDep,
    service: AdminPlaySessionServiceDep,
) -> AdminPlaySessionDetail:
    """Force-end a stuck active play_session now (409 if it already ended)."""
    try:
        return await service.clamp_play_session(admin, public_id)
    except PlaySessionNotFoundError:
        raise _not_found() from None
    except PlaySessionNotActiveError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="PlaySession has already ended.",
        ) from None


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PlaySession not found")
