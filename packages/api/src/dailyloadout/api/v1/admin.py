"""Backoffice (internal) API.

Served under ``/internal/...`` — a deliberately non-advertising prefix that the
reverse proxy can deny from the public web origin (edge defense-in-depth),
while the URL avoids the word "admin" that invites drive-by exploit scans.

Every route here is gated by ``AdminUserDep`` (a backoffice admin grant in the
``admin_users`` table). This Phase-1 surface only exposes a whoami check the
backoffice SPA uses to confirm access; user/game/config management lands in
later phases.
"""

from __future__ import annotations

from fastapi import APIRouter

from dailyloadout.core.admin.schemas import AdminMeResponse
from dailyloadout.deps.auth import AdminUserDep

router = APIRouter(prefix="/internal/v1", tags=["internal"])


@router.get("/me", response_model=AdminMeResponse)
async def admin_me(admin: AdminUserDep) -> AdminMeResponse:
    """Return the current admin's identity; 403 for non-admins."""
    return AdminMeResponse.model_validate(admin)
