"""Backoffice captures moderation API (Epic 21, Phase 6).

Served under ``/internal/v1/captures`` — a separate module from ``admin.py`` to
keep each router file within the 300-line budget. Every route is admin-gated and
mutations are audited like the rest of the backoffice.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from slate.api.v1._cost_guard import cost_guard
from slate.api.v1._rate_limit import rate_limit
from slate.config import settings
from slate.core.admin.captures_service import (
    CaptureNotFoundError,
    CaptureNotReprocessableError,
)
from slate.core.admin.schemas import AdminCaptureDetail, AdminCaptureList
from slate.deps.auth import AdminCaptureServiceDep, AdminUserDep

router = APIRouter(prefix="/internal/v1", tags=["internal"])

# Reprocess re-runs the full LLM/IGDB capture pipeline, so meter it like the
# user-facing submit path — a rogue/leaked admin token shouldn't be able to loop
# it to drive Ollama/IGDB cost. The generic middleware limiter is only a
# fail-open backstop.
_reprocess_rate_limit = Depends(
    rate_limit(
        "admin_capture_reprocess",
        settings.rate_limit_capture_submit_per_minute,
        60,
        by="user",
        fail_closed=True,
    )
)
_reprocess_cost_guard = Depends(cost_guard("capture"))


@router.get("/captures", response_model=AdminCaptureList)
async def list_captures(
    _admin: AdminUserDep,
    service: AdminCaptureServiceDep,
    q: str | None = Query(default=None, description="Match the owner's email"),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AdminCaptureList:
    """List/search captures across all users with per-status tallies (paginated)."""
    return await service.list_captures(query=q, status=status_filter, limit=limit, offset=offset)


@router.get("/captures/{public_id}", response_model=AdminCaptureDetail)
async def get_capture(
    public_id: UUID,
    _admin: AdminUserDep,
    service: AdminCaptureServiceDep,
) -> AdminCaptureDetail:
    """Return the full backoffice view of a single capture (with candidates)."""
    try:
        return await service.get_capture(public_id)
    except CaptureNotFoundError:
        raise _not_found() from None


@router.post(
    "/captures/{public_id}/reprocess",
    response_model=AdminCaptureDetail,
    dependencies=[_reprocess_rate_limit, _reprocess_cost_guard],
)
async def reprocess_capture(
    public_id: UUID,
    admin: AdminUserDep,
    service: AdminCaptureServiceDep,
) -> AdminCaptureDetail:
    """Re-run the pipeline for a stuck/failed text capture (clears old candidates)."""
    try:
        return await service.reprocess_capture(admin, public_id)
    except CaptureNotFoundError:
        raise _not_found() from None
    except CaptureNotReprocessableError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Capture has no re-runnable source (its upload was discarded).",
        ) from None


@router.delete("/captures/{public_id}", status_code=status.HTTP_204_NO_CONTENT)
async def purge_capture(
    public_id: UUID,
    admin: AdminUserDep,
    service: AdminCaptureServiceDep,
) -> None:
    """Hard-delete a capture and its candidates (audited)."""
    try:
        await service.purge_capture(admin, public_id)
    except CaptureNotFoundError:
        raise _not_found() from None


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capture not found")
