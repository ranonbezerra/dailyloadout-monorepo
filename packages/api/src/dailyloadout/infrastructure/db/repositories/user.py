"""Repository for the ``users`` table."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dailyloadout.infrastructure.db.models import User


class UserRepository:
    """Thin data-access layer around the ``users`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: int) -> User | None:
        """Return the user with the given internal *user_id*, or ``None``."""
        stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Return the active user with *email*, or ``None``."""
        stmt = select(User).where(User.email == email, User.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_public_id(self, public_id: UUID) -> User | None:
        """Return the active user with *public_id*, or ``None``."""
        stmt = select(User).where(User.public_id == public_id, User.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, email: str, password_hash: str, display_name: str) -> User:
        """Insert a new user and return the persisted instance."""
        user = User(
            email=email,
            password_hash=password_hash,
            display_name=display_name,
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def email_exists(self, email: str) -> bool:
        """Return ``True`` if an active user with *email* already exists."""
        stmt = select(User.id).where(User.email == email, User.deleted_at.is_(None)).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
