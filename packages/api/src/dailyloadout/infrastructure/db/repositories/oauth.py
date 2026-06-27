"""Repository for the ``oauth_identities`` table."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dailyloadout.infrastructure.db.models.auth import OAuthIdentity


class OAuthIdentityRepository:
    """Thin data-access layer around the ``oauth_identities`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_provider_uid(self, provider: str, provider_uid: str) -> OAuthIdentity | None:
        """Return the identity for ``(provider, provider_uid)``, or ``None``."""
        stmt = select(OAuthIdentity).where(
            OAuthIdentity.provider == provider,
            OAuthIdentity.provider_uid == provider_uid,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self, user_id: int, provider: str, provider_uid: str, email: str
    ) -> OAuthIdentity:
        """Link a provider identity to *user_id* and return the row."""
        identity = OAuthIdentity(
            user_id=user_id,
            provider=provider,
            provider_uid=provider_uid,
            email=email,
        )
        self._session.add(identity)
        await self._session.flush()
        return identity
