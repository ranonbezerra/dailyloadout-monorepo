"""Repository for the ``refresh_tokens`` table."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select, update
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

    async def get_any_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Return the token matching *token_hash* regardless of revoked/expired state.

        Used by refresh-reuse detection: a hash that is absent from the active
        lookup but present here means an already-rotated/revoked token was
        replayed — a theft signal.
        """
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, token_id: int) -> None:
        """Mark a single refresh token as revoked."""
        now = datetime.now(UTC)
        stmt = update(RefreshToken).where(RefreshToken.id == token_id).values(revoked_at=now)
        await self._session.execute(stmt)

    async def count_active_for_user(self, user_id: int) -> int:
        """Return how many non-revoked, non-expired sessions *user_id* has."""
        now = datetime.now(UTC)
        total = await self._session.scalar(
            select(func.count())
            .select_from(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
        )
        return total or 0

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

    async def commit(self) -> None:
        """Flush and commit the current transaction.

        Used by incident-response paths (e.g. refresh-token reuse detection)
        that must durably persist a security write even though the request then
        raises and returns an error response (which would otherwise roll back).
        """
        await self._session.commit()
