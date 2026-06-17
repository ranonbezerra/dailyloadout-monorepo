"""Repository for the ``refresh_tokens`` table."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from dailyloadout.infrastructure.db.models import RefreshToken


class RefreshTokenRepository:
    """Thin data-access layer around the ``refresh_tokens`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        user_id: int,
        token_hash: str,
        expires_at: datetime,
        device_label: str | None = None,
    ) -> RefreshToken:
        """Insert a new refresh token row and return it."""
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            device_label=device_label,
        )
        self._session.add(token)
        await self._session.flush()
        return token

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Return the active (not revoked, not expired) token matching *token_hash*."""
        now = datetime.now(UTC)
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, token_id: int) -> None:
        """Mark a single refresh token as revoked."""
        now = datetime.now(UTC)
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.id == token_id)
            .values(revoked_at=now)
        )
        await self._session.execute(stmt)

    async def revoke_all_for_user(self, user_id: int) -> None:
        """Revoke every active refresh token belonging to *user_id*."""
        now = datetime.now(UTC)
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        await self._session.execute(stmt)
