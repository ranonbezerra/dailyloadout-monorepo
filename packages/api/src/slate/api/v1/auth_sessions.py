"""Session (device) management endpoints: list active sessions + revoke one.

Complements ``/logout`` (this device) and ``/logout-all`` (everything) with
granular control: see where you're signed in and sign out a single device.
Revocation is owner-scoped in the query, so a handle can only ever revoke the
caller's own session.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from slate.core.auth.schemas import SessionResponse
from slate.deps.account import SessionServiceDep
from slate.deps.auth import CurrentUserDep

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    current_user: CurrentUserDep,
    service: SessionServiceDep,
) -> list[SessionResponse]:
    """List the caller's active sessions (devices), newest first."""
    sessions = await service.list_sessions(current_user)
    return [SessionResponse.model_validate(s) for s in sessions]


@router.delete("/sessions/{public_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    public_id: UUID,
    current_user: CurrentUserDep,
    service: SessionServiceDep,
) -> None:
    """Revoke one of the caller's sessions by handle (sign out that device)."""
    revoked = await service.revoke_session(current_user, public_id)
    if not revoked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
