"""Backoffice (internal) API.

Served under ``/internal/...`` — a deliberately non-advertising prefix that the
reverse proxy can deny from the public web origin (edge defense-in-depth),
while the URL avoids the word "admin" that invites drive-by exploit scans.

Every route here is gated by ``AdminUserDep`` (a backoffice admin grant in the
``admin_users`` table). Phase 1 exposed only a whoami check; Phase 2 adds user
management (list/search, inspect, ban/unban/verify) and the audit log that
records every mutation.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from dailyloadout.core.admin.config_service import UnknownConfigKeyError
from dailyloadout.core.admin.games_service import GameNotFoundError
from dailyloadout.core.admin.schemas import (
    AdminAuditListResponse,
    AdminGameDetail,
    AdminGameList,
    AdminMeResponse,
    AdminUserDetail,
    AdminUserListResponse,
    BanRequest,
    ConfigListResponse,
    ConfigSetRequest,
    DashboardSummary,
    GameEditRequest,
)
from dailyloadout.core.admin.service import AdminUserNotFoundError, CannotModerateAdminError
from dailyloadout.deps.auth import (
    AdminConfigServiceDep,
    AdminDashboardServiceDep,
    AdminGameServiceDep,
    AdminUserDep,
    AdminUserServiceDep,
)
from dailyloadout.infrastructure.config.registry import ConfigValidationError

router = APIRouter(prefix="/internal/v1", tags=["internal"])


@router.get("/me", response_model=AdminMeResponse)
async def admin_me(admin: AdminUserDep) -> AdminMeResponse:
    """Return the current admin's identity; 403 for non-admins."""
    return AdminMeResponse.model_validate(admin)


@router.get("/dashboard", response_model=DashboardSummary)
async def dashboard(
    _admin: AdminUserDep,
    service: AdminDashboardServiceDep,
) -> DashboardSummary:
    """Return at-a-glance backoffice metrics for the admin landing screen."""
    return await service.summary()


# ── Users management ────────────────────────────────────────────────────


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    _admin: AdminUserDep,
    service: AdminUserServiceDep,
    q: str | None = Query(default=None, description="Match email or display name"),
    banned: bool | None = Query(default=None),
    verified: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AdminUserListResponse:
    """List/search users with optional ban/verification filters (paginated)."""
    return await service.list_users(
        query=q,
        is_banned=banned,
        email_verified=verified,
        limit=limit,
        offset=offset,
    )


@router.get("/users/{public_id}", response_model=AdminUserDetail)
async def get_user(
    public_id: UUID,
    _admin: AdminUserDep,
    service: AdminUserServiceDep,
) -> AdminUserDetail:
    """Return the full backoffice view of a single user."""
    try:
        return await service.get_user(public_id)
    except AdminUserNotFoundError:
        raise _not_found() from None


@router.post("/users/{public_id}/ban", response_model=AdminUserDetail)
async def ban_user(
    public_id: UUID,
    admin: AdminUserDep,
    service: AdminUserServiceDep,
    body: BanRequest | None = None,
) -> AdminUserDetail:
    """Ban a user (cuts off all access). Refuses to ban another admin."""
    reason = body.reason if body else None
    try:
        return await service.ban_user(admin, public_id, reason)
    except AdminUserNotFoundError:
        raise _not_found() from None
    except CannotModerateAdminError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot ban an admin user; revoke the admin grant first.",
        ) from None


@router.post("/users/{public_id}/unban", response_model=AdminUserDetail)
async def unban_user(
    public_id: UUID,
    admin: AdminUserDep,
    service: AdminUserServiceDep,
) -> AdminUserDetail:
    """Lift a user's ban (they may log in again; sessions are not re-minted)."""
    try:
        return await service.unban_user(admin, public_id)
    except AdminUserNotFoundError:
        raise _not_found() from None


@router.post("/users/{public_id}/verify", response_model=AdminUserDetail)
async def verify_user(
    public_id: UUID,
    admin: AdminUserDep,
    service: AdminUserServiceDep,
) -> AdminUserDetail:
    """Force-mark a user's email as verified (idempotent)."""
    try:
        return await service.verify_user(admin, public_id)
    except AdminUserNotFoundError:
        raise _not_found() from None


# ── Audit log ───────────────────────────────────────────────────────────


@router.get("/audit", response_model=AdminAuditListResponse)
async def list_audit(
    _admin: AdminUserDep,
    service: AdminUserServiceDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AdminAuditListResponse:
    """Return a newest-first page of audited admin actions."""
    return await service.list_audit(limit=limit, offset=offset)


# ── Dynamic operational config ──────────────────────────────────────────


@router.get("/config", response_model=ConfigListResponse)
async def list_config(
    _admin: AdminUserDep,
    service: AdminConfigServiceDep,
) -> ConfigListResponse:
    """List every curated knob with effective/override/baseline values."""
    return await service.list_config()


@router.put("/config/{key}", response_model=ConfigListResponse)
async def set_config(
    key: str,
    body: ConfigSetRequest,
    admin: AdminUserDep,
    service: AdminConfigServiceDep,
) -> ConfigListResponse:
    """Set a runtime override for *key* (validated, audited, cache-invalidated)."""
    try:
        return await service.set_override(admin, key, body.value)
    except UnknownConfigKeyError:
        raise _unknown_key(key) from None
    except ConfigValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from None


@router.delete("/config/{key}", response_model=ConfigListResponse)
async def clear_config(
    key: str,
    admin: AdminUserDep,
    service: AdminConfigServiceDep,
) -> ConfigListResponse:
    """Clear *key*'s override, reverting it to the env/code baseline (audited)."""
    try:
        return await service.clear_override(admin, key)
    except UnknownConfigKeyError:
        raise _unknown_key(key) from None


# ── Catalogue (games) ───────────────────────────────────────────────────


@router.get("/games", response_model=AdminGameList)
async def list_games(
    _admin: AdminUserDep,
    service: AdminGameServiceDep,
    q: str | None = Query(default=None, description="Match title or slug"),
    shared: bool | None = Query(default=None),
    source: str | None = Query(default=None, pattern="^(igdb|manual)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AdminGameList:
    """List/search the catalogue with owner counts + provenance filters."""
    return await service.list_games(
        query=q, is_shared=shared, source=source, limit=limit, offset=offset
    )


@router.get("/games/{public_id}", response_model=AdminGameDetail)
async def get_game(
    public_id: UUID,
    _admin: AdminUserDep,
    service: AdminGameServiceDep,
) -> AdminGameDetail:
    """Return the full backoffice view of a single game."""
    try:
        return await service.get_game(public_id)
    except GameNotFoundError:
        raise _game_not_found() from None


@router.post("/games/{public_id}/demote", response_model=AdminGameDetail)
async def demote_game(
    public_id: UUID,
    admin: AdminUserDep,
    service: AdminGameServiceDep,
) -> AdminGameDetail:
    """Demote a shared row back to private (removes it from the catalogue)."""
    try:
        return await service.demote_game(admin, public_id)
    except GameNotFoundError:
        raise _game_not_found() from None


@router.post("/games/{public_id}/promote", response_model=AdminGameDetail)
async def promote_game(
    public_id: UUID,
    admin: AdminUserDep,
    service: AdminGameServiceDep,
) -> AdminGameDetail:
    """Promote a private manual row into the shared catalogue."""
    try:
        return await service.promote_game(admin, public_id)
    except GameNotFoundError:
        raise _game_not_found() from None


@router.patch("/games/{public_id}", response_model=AdminGameDetail)
async def edit_game(
    public_id: UUID,
    body: GameEditRequest,
    admin: AdminUserDep,
    service: AdminGameServiceDep,
) -> AdminGameDetail:
    """Edit a game's title/summary (only provided fields change)."""
    try:
        return await service.edit_game(admin, public_id, body)
    except GameNotFoundError:
        raise _game_not_found() from None


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


def _game_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")


def _unknown_key(key: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown config key: {key}"
    )
