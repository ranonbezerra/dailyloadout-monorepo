"""Repository for the ``admin_users`` grant table.

A row in ``admin_users`` is the sole source of truth for backoffice admin
rights. Admin-ness is checked here per request (cheap, indexed by the unique
``user_id``) rather than carried in the JWT, so revoking a grant takes effect
immediately.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dailyloadout.infrastructure.db.models import AdminUser


class AdminRepository:
    """Thin data-access layer around the ``admin_users`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def is_admin(self, user_id: int) -> bool:
        """Return ``True`` if *user_id* has an admin grant."""
        stmt = select(AdminUser.id).where(AdminUser.user_id == user_id).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

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
