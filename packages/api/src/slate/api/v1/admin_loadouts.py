"""Backoffice loadouts read-only API (Epic 21, Phase 6).

Served under ``/internal/v1/loadouts`` — a separate module from ``admin.py`` to
keep each router file within the 300-line budget. Read-only: loadouts decay on
their own via the auto-ignore worker, so the backoffice only browses them.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from slate.core.admin.loadouts_schemas import AdminLoadoutDetail, AdminLoadoutList
from slate.core.admin.loadouts_service import LoadoutNotFoundError
from slate.deps.admin import AdminLoadoutServiceDep
from slate.deps.auth import AdminUserDep

router = APIRouter(prefix="/internal/v1", tags=["internal"])

_ACTION_PATTERN = "^(pending|accepted|rejected|ignored)$"


@router.get("/loadouts", response_model=AdminLoadoutList)
async def list_loadouts(
    _admin: AdminUserDep,
    service: AdminLoadoutServiceDep,
    q: str | None = Query(default=None, description="Match the owner's email"),
    action: str | None = Query(default=None, pattern=_ACTION_PATTERN),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AdminLoadoutList:
    """List/search loadouts across all users with per-action tallies (paginated)."""
    return await service.list_loadouts(query=q, action=action, limit=limit, offset=offset)


@router.get("/loadouts/{public_id}", response_model=AdminLoadoutDetail)
async def get_loadout(
    public_id: UUID,
    _admin: AdminUserDep,
    service: AdminLoadoutServiceDep,
) -> AdminLoadoutDetail:
    """Return the full backoffice view of a single loadout suggestion."""
    try:
        return await service.get_loadout(public_id)
    except LoadoutNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Loadout not found"
        ) from None
