"""Repository for the ``refresh_tokens`` table."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from slate.infrastructure.db.models import RefreshToken


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

    async def revoke(self, token_id: int) -> bool:
        """Atomically revoke a token, but ONLY while it's still active.

        Conditional UPDATE (``WHERE revoked_at IS NULL``) so two concurrent
        rotations of the SAME valid token can't both revoke-and-mint: the loser
        matches 0 rows and the caller rejects it. This closes the rotation race
        that reuse-detection would otherwise miss (neither request replays the
        rotated hash). Returns ``True`` if this call revoked it.
        """
        now = datetime.now(UTC)
        result = await self._session.execute(
            update(RefreshToken)
            .where(RefreshToken.id == token_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        return (cast("CursorResult[Any]", result).rowcount or 0) > 0

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

    async def list_active_for_user(self, user_id: int) -> list[RefreshToken]:
        """Return *user_id*'s active (non-revoked, non-expired) sessions, newest first."""
        now = datetime.now(UTC)
        result = await self._session.execute(
            select(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
            .order_by(RefreshToken.last_used_at.desc().nullslast(), RefreshToken.created_at.desc())
        )
        return list(result.scalars().all())

    async def revoke_by_public_id(self, user_id: int, public_id: UUID) -> bool:
        """Revoke one active session by its handle, scoped to *user_id*.

        Conditional UPDATE (``WHERE public_id AND user_id AND revoked_at IS NULL``)
        so a user can only revoke their own live session; returns whether a row was
        revoked (False = unknown/already-revoked/another user's).
        """
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.public_id == public_id,
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        result = await self._session.execute(stmt)
        return (cast("CursorResult[Any]", result).rowcount or 0) > 0

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
