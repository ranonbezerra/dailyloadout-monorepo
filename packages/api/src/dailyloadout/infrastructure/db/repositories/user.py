"""Repository for the ``users`` table."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ColumnElement, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from dailyloadout.infrastructure.db.models import User


def _normalize_email(email: str) -> str:
    """Trim and lowercase an email for consistent storage and lookup."""
    return email.strip().lower()


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
        """Return the active user with *email* (normalized), or ``None``."""
        stmt = select(User).where(User.email == _normalize_email(email), User.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_public_id(self, public_id: UUID) -> User | None:
        """Return the active user with *public_id*, or ``None``."""
        stmt = select(User).where(User.public_id == public_id, User.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        email: str,
        password_hash: str,
        display_name: str,
        email_verified: bool = False,
    ) -> User:
        """Insert a new user (email normalized) and return the instance."""
        user = User(
            email=_normalize_email(email),
            password_hash=password_hash,
            display_name=display_name,
            email_verified=email_verified,
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def create_oauth_user(
        self,
        email: str,
        display_name: str,
        *,
        email_verified: bool,
        avatar_url: str | None = None,
    ) -> User:
        """Insert a passwordless user from a social login and return it.

        ``password_hash`` is ``None`` (the account has no password until the
        user sets one); login() already rejects passwordless accounts.
        """
        user = User(
            email=_normalize_email(email),
            password_hash=None,
            display_name=display_name,
            email_verified=email_verified,
            avatar_url=avatar_url,
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def email_exists(self, email: str) -> bool:
        """Return ``True`` if an active user with *email* (normalized) exists."""
        stmt = (
            select(User.id)
            .where(User.email == _normalize_email(email), User.deleted_at.is_(None))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def set_email_verified(self, user: User) -> None:
        """Mark *user*'s email as verified (idempotent)."""
        user.email_verified = True
        await self._session.flush()

    async def bump_token_version(self, user_id: int) -> None:
        """Increment *user_id*'s ``token_version`` (kills outstanding access tokens)."""
        stmt = update(User).where(User.id == user_id).values(token_version=User.token_version + 1)
        await self._session.execute(stmt)

    async def set_banned(self, user_id: int, banned: bool) -> None:
        """Set *user_id*'s ``is_banned`` flag to *banned*."""
        stmt = update(User).where(User.id == user_id).values(is_banned=banned)
        await self._session.execute(stmt)

    async def search(
        self,
        *,
        query: str | None = None,
        is_banned: bool | None = None,
        email_verified: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[User], int]:
        """Return a page of active users plus the total matching count.

        *query* matches case-insensitively against email or display name;
        *is_banned* / *email_verified* filter by those flags when not ``None``.
        Results are newest-first. The total reflects all matches, not the page.
        """
        conditions: list[ColumnElement[bool]] = [User.deleted_at.is_(None)]
        if query:
            pattern = f"%{query.strip()}%"
            conditions.append(or_(User.email.ilike(pattern), User.display_name.ilike(pattern)))
        if is_banned is not None:
            conditions.append(User.is_banned.is_(is_banned))
        if email_verified is not None:
            conditions.append(User.email_verified.is_(email_verified))

        total = await self._session.scalar(
            select(func.count()).select_from(User).where(*conditions)
        )
        rows = (
            (
                await self._session.execute(
                    select(User)
                    .where(*conditions)
                    .order_by(User.created_at.desc(), User.id.desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total or 0
