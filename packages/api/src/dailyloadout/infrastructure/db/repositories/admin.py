"""Repository for the ``admin_users`` grant table.

A row in ``admin_users`` is the sole source of truth for backoffice admin
rights. Admin-ness is checked here per request (cheap, indexed by the unique
``user_id``) rather than carried in the JWT, so revoking a grant takes effect
immediately.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from dailyloadout.infrastructure.db.models import AdminAuditLog, AdminUser, User


@dataclass(frozen=True, slots=True)
class AuditEntryRow:
    """A denormalised audit entry: the action plus the actor/target identities.

    The repository resolves both user FKs to their public_id + email in one
    query so the service never has to issue per-row lookups for display.
    """

    action: str
    detail: str | None
    created_at: datetime
    admin_public_id: UUID | None
    admin_email: str | None
    target_public_id: UUID | None
    target_email: str | None


class AdminRepository:
    """Thin data-access layer around the ``admin_users`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def is_admin(self, user_id: int) -> bool:
        """Return ``True`` if *user_id* has an admin grant."""
        stmt = select(AdminUser.id).where(AdminUser.user_id == user_id).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def count(self) -> int:
        """Return how many users hold an admin grant."""
        total = await self._session.scalar(select(func.count()).select_from(AdminUser))
        return total or 0

    async def grant(self, user_id: int, granted_by: int | None = None) -> AdminUser:
        """Grant admin to *user_id* (idempotent: returns the existing grant).

        *granted_by* records who issued the grant (``None`` for a CLI/bootstrap
        grant) for the audit trail.
        """
        stmt = select(AdminUser).where(AdminUser.user_id == user_id)
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            return existing

        grant = AdminUser(user_id=user_id, granted_by=granted_by)
        self._session.add(grant)
        await self._session.flush()
        return grant

    async def revoke(self, user_id: int) -> bool:
        """Revoke *user_id*'s admin grant. Return ``True`` if one was removed."""
        stmt = select(AdminUser).where(AdminUser.user_id == user_id)
        grant = (await self._session.execute(stmt)).scalar_one_or_none()
        if grant is None:
            return False
        await self._session.delete(grant)
        await self._session.flush()
        return True


class AdminAuditRepository:
    """Append-only writer/reader for the ``admin_audit_log`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        *,
        admin_user_id: int,
        action: str,
        target_user_id: int | None = None,
        detail: str | None = None,
    ) -> AdminAuditLog:
        """Append an audit entry for a mutating admin action."""
        entry = AdminAuditLog(
            admin_user_id=admin_user_id,
            action=action,
            target_user_id=target_user_id,
            detail=detail,
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def list_recent(
        self, *, limit: int = 50, offset: int = 0
    ) -> tuple[list[AuditEntryRow], int]:
        """Return a newest-first page of audit entries plus the total count.

        Both user FKs are resolved (LEFT JOIN — a ``SET NULL`` actor/target
        still yields a row) to their public_id + email for display.
        """
        actor = aliased(User)
        target = aliased(User)
        total = await self._session.scalar(select(func.count()).select_from(AdminAuditLog))
        result = await self._session.execute(
            select(
                AdminAuditLog.action,
                AdminAuditLog.detail,
                AdminAuditLog.created_at,
                actor.public_id,
                actor.email,
                target.public_id,
                target.email,
            )
            .outerjoin(actor, AdminAuditLog.admin_user_id == actor.id)
            .outerjoin(target, AdminAuditLog.target_user_id == target.id)
            .order_by(AdminAuditLog.created_at.desc(), AdminAuditLog.id.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = [
            AuditEntryRow(
                action=r[0],
                detail=r[1],
                created_at=r[2],
                admin_public_id=r[3],
                admin_email=r[4],
                target_public_id=r[5],
                target_email=r[6],
            )
            for r in result.all()
        ]
        return rows, total or 0
