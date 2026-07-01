"""Session (device) management: list active sessions + revoke one by its handle.

A thin seam over the refresh-token repo — the user sees where they're signed in
and can sign out an individual device, complementing the blanket ``logout-all``.
Revocation is owner-scoped in the query, so one user can never revoke another's.
"""

from __future__ import annotations

from uuid import UUID

from slate.infrastructure.db.models import RefreshToken, User
from slate.infrastructure.db.repositories.refresh_token import RefreshTokenRepository


class SessionService:
    """List + revoke a user's active refresh-token sessions."""

    def __init__(self, refresh_tokens: RefreshTokenRepository) -> None:
        self._refresh_tokens = refresh_tokens

    async def list_sessions(self, user: User) -> list[RefreshToken]:
        """The caller's active (non-revoked, non-expired) sessions, newest first."""
        return await self._refresh_tokens.list_active_for_user(user.id)

    async def revoke_session(self, user: User, public_id: UUID) -> bool:
        """Revoke one of the caller's sessions by handle. False if it isn't theirs/active."""
        return await self._refresh_tokens.revoke_by_public_id(user.id, public_id)
