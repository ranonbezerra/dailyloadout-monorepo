"""Backoffice picks read-only API (Epic 21, Phase 6).

Served under ``/internal/v1/picks`` — a separate module from ``admin.py`` to
keep each router file within the 300-line budget. Read-only: picks decay on
their own via the auto-ignore worker, so the backoffice only browses them.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from slate.core.admin.picks_schemas import AdminPickDetail, AdminPickList
from slate.core.admin.picks_service import PickNotFoundError
from slate.deps.admin import AdminPickServiceDep
from slate.deps.auth import AdminUserDep

router = APIRouter(prefix="/internal/v1", tags=["internal"])

_ACTION_PATTERN = "^(pending|accepted|rejected|ignored)$"


@router.get("/picks", response_model=AdminPickList)
async def list_picks(
    _admin: AdminUserDep,
    service: AdminPickServiceDep,
    q: str | None = Query(default=None, description="Match the owner's email"),
    action: str | None = Query(default=None, pattern=_ACTION_PATTERN),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AdminPickList:
    """List/search picks across all users with per-action tallies (paginated)."""
    return await service.list_picks(query=q, action=action, limit=limit, offset=offset)


@router.get("/picks/{public_id}", response_model=AdminPickDetail)
async def get_pick(
    public_id: UUID,
    _admin: AdminUserDep,
    service: AdminPickServiceDep,
) -> AdminPickDetail:
    """Return the full backoffice view of a single pick suggestion."""
    try:
        return await service.get_pick(public_id)
    except PickNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pick not found"
        ) from None
