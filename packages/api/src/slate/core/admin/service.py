"""Backoffice user-management service (Epic 21, Phase 2).

Orchestrates the admin actions on user accounts — list/search, inspect, and the
incident-response mutations (ban / unban / verify) — on top of the existing auth
primitives. Every mutation writes an :class:`AdminAuditLog` row so the DoD's
"every change audited" holds by construction. Layer discipline: this service
calls repositories and the auth service only; it never touches a Session.
"""

from __future__ import annotations

from uuid import UUID

from slate.core.admin.logging import log_admin_event
from slate.core.admin.schemas import (
    AdminAuditEntry,
    AdminAuditListResponse,
    AdminUserDetail,
    AdminUserListResponse,
    AdminUserSummary,
)
from slate.core.auth.service import AuthService
from slate.infrastructure.db.models import User
from slate.infrastructure.db.repositories.admin import AdminAuditRepository, AdminRepository
from slate.infrastructure.db.repositories.refresh_token import RefreshTokenRepository
from slate.infrastructure.db.repositories.user import UserRepository


class AdminUserNotFoundError(Exception):
    """Raised when a backoffice action targets an unknown user public_id."""


class CannotModerateAdminError(Exception):
    """Raised when an admin tries to ban another admin (privilege protection)."""


# Audit action identifiers (stable strings stored in admin_audit_log.action).
ACTION_BAN = "user.ban"
ACTION_UNBAN = "user.unban"
ACTION_VERIFY = "user.verify"


class AdminUserService:
    """User-management operations for the backoffice."""

    def __init__(
        self,
        user_repo: UserRepository,
        admin_repo: AdminRepository,
        audit_repo: AdminAuditRepository,
        refresh_token_repo: RefreshTokenRepository,
        auth_service: AuthService,
    ) -> None:
        self._users = user_repo
        self._admins = admin_repo
        self._audit = audit_repo
        self._tokens = refresh_token_repo
        self._auth = auth_service

    # ── Read ──
    async def list_users(
        self,
        *,
        query: str | None,
        is_banned: bool | None,
        email_verified: bool | None,
        limit: int,
        offset: int,
    ) -> AdminUserListResponse:
        """Return a page of users matching the given search/filter criteria."""
        users, total = await self._users.search(
            query=query,
            is_banned=is_banned,
            email_verified=email_verified,
            limit=limit,
            offset=offset,
        )
        return AdminUserListResponse(
            items=[AdminUserSummary.model_validate(u) for u in users],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_user(self, public_id: UUID) -> AdminUserDetail:
        """Return the full backoffice view of one user, or raise if unknown."""
        user = await self._require_user(public_id)
        return await self._build_detail(user)

    # ── Mutations (audited) ──
    async def ban_user(self, actor: User, public_id: UUID, reason: str | None) -> AdminUserDetail:
        """Ban *public_id*: cut off all access and record the action.

        Refuses to ban another admin (or oneself) — moderating peers is a
        privilege fight the backoffice must not enable; revoke the grant first.
        """
        user = await self._require_user(public_id)
        if await self._admins.is_admin(user.id):
            raise CannotModerateAdminError
        await self._auth.ban_user(user.id)
        user.is_banned = True  # reflect the bulk UPDATE on the loaded instance
        await self._audit.record(
            admin_user_id=actor.id,
            action=ACTION_BAN,
            target_user_id=user.id,
            detail=reason,
        )
        log_admin_event(
            "admin_user_banned",
            actor=actor,
            action=ACTION_BAN,
            target_user=user,
            reason_present=reason is not None,
        )
        return await self._build_detail(user)

    async def unban_user(self, actor: User, public_id: UUID) -> AdminUserDetail:
        """Lift the ban on *public_id* (does not re-mint sessions)."""
        user = await self._require_user(public_id)
        await self._users.set_banned(user.id, False)
        user.is_banned = False
        await self._audit.record(
            admin_user_id=actor.id,
            action=ACTION_UNBAN,
            target_user_id=user.id,
        )
        log_admin_event("admin_user_unbanned", actor=actor, action=ACTION_UNBAN, target_user=user)
        return await self._build_detail(user)

    async def verify_user(self, actor: User, public_id: UUID) -> AdminUserDetail:
        """Force-mark *public_id*'s email as verified (idempotent)."""
        user = await self._require_user(public_id)
        if not user.email_verified:
            await self._users.set_email_verified(user)
        await self._audit.record(
            admin_user_id=actor.id,
            action=ACTION_VERIFY,
            target_user_id=user.id,
        )
        log_admin_event("admin_user_verified", actor=actor, action=ACTION_VERIFY, target_user=user)
        return await self._build_detail(user)

    # ── Audit ──
    async def list_audit(self, *, limit: int, offset: int) -> AdminAuditListResponse:
        """Return a newest-first page of audited admin actions."""
        rows, total = await self._audit.list_recent(limit=limit, offset=offset)
        return AdminAuditListResponse(
            items=[
                AdminAuditEntry(
                    action=r.action,
                    detail=r.detail,
                    created_at=r.created_at,
                    admin_public_id=r.admin_public_id,
                    admin_email=r.admin_email,
                    target_public_id=r.target_public_id,
                    target_email=r.target_email,
                )
                for r in rows
            ],
            total=total,
            limit=limit,
            offset=offset,
        )

    # ── Internals ──
    async def _require_user(self, public_id: UUID) -> User:
        user = await self._users.get_by_public_id(public_id)
        if user is None:
            raise AdminUserNotFoundError
        return user

    async def _build_detail(self, user: User) -> AdminUserDetail:
        is_admin = await self._admins.is_admin(user.id)
        active_sessions = await self._tokens.count_active_for_user(user.id)
        return AdminUserDetail(
            public_id=user.public_id,
            email=user.email,
            display_name=user.display_name,
            email_verified=user.email_verified,
            is_banned=user.is_banned,
            created_at=user.created_at,
            avatar_url=user.avatar_url,
            locale=user.locale,
            timezone=user.timezone,
            is_admin=is_admin,
            has_password=user.password_hash is not None,
            active_sessions=active_sessions,
        )
