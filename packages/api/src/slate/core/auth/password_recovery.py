"""Password recovery: forgot-password, reset-password, change-password.

Kept separate from :class:`~slate.core.auth.service.AuthService` so each module
stays focused (and under the 300-line cap). All three flows funnel through
:meth:`_apply_new_password`, which sets the hash, kills every existing session
(``token_version`` bump + refresh-token revoke), and sends a security notice.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from slate.core.auth.security import (
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    create_password_reset_token,
    decode_password_reset_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from slate.infrastructure.db.models import User
from slate.infrastructure.db.repositories.refresh_token import RefreshTokenRepository
from slate.infrastructure.db.repositories.user import UserRepository
from slate.infrastructure.email import (
    Mailer,
    get_mailer,
    send_password_changed_email,
    send_password_reset_email,
)

__all__ = ["PasswordRecoveryService"]


class PasswordRecoveryService:
    """Orchestrates the forgot / reset / change password flows."""

    def __init__(
        self,
        user_repo: UserRepository,
        refresh_token_repo: RefreshTokenRepository,
        mailer: Mailer | None = None,
    ) -> None:
        self._user_repo = user_repo
        self._refresh_token_repo = refresh_token_repo
        self._mailer = mailer or get_mailer()

    async def forgot_password(self, email: str) -> None:
        """Best-effort send of a reset link. Neutral by design.

        Never reveals whether the account exists: the caller always gets the
        same response whether or not an email was actually sent.
        """
        user = await self._user_repo.get_by_email(email)
        if user is None:
            return
        token = create_password_reset_token(str(user.public_id))
        send_password_reset_email(self._mailer, to=user.email, token=token)

    async def reset_password(self, token: str, new_password: str) -> None:
        """Validate a reset *token*, set the new password, and kill all sessions.

        Raises:
            ValueError: if the token is invalid/expired or the user is unknown.
        """
        public_id = self._decode_reset_subject(token)
        user = await self._user_repo.get_by_public_id(public_id)
        if user is None:
            raise ValueError("Invalid or expired reset token")
        await self._apply_new_password(user, new_password)

    async def change_password(
        self, user: User, current_password: str, new_password: str
    ) -> tuple[str, str]:
        """Verify the current password, set a new one, and reissue tokens.

        Kills every *other* session (``token_version`` bump + refresh revoke)
        but keeps the calling device signed in by returning a fresh token pair.

        Returns:
            ``(access_token, raw_refresh_token)``

        Raises:
            ValueError: if the current password is missing or incorrect.
        """
        if user.password_hash is None or not verify_password(current_password, user.password_hash):
            raise ValueError("Current password is incorrect")

        await self._apply_new_password(user, new_password)

        access_token = create_access_token(str(user.public_id), user.token_version)
        raw_refresh = generate_refresh_token()
        await self._store_refresh_token(user.id, raw_refresh)
        return access_token, raw_refresh

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    @staticmethod
    def _decode_reset_subject(token: str) -> UUID:
        """Decode a reset token to its subject UUID (raises on bad token)."""
        public_id_str = decode_password_reset_token(token)
        try:
            return UUID(public_id_str)
        except ValueError as exc:
            raise ValueError("Invalid or expired reset token") from exc

    async def _apply_new_password(self, user: User, new_password: str) -> None:
        """Set the hash, cut off all sessions, and send the security notice."""
        await self._user_repo.set_password_and_bump(user, hash_password(new_password))
        await self._refresh_token_repo.revoke_all_for_user(user.id)
        send_password_changed_email(self._mailer, to=user.email)

    async def _store_refresh_token(self, user_id: int, raw_token: str) -> None:
        """Hash *raw_token* and persist it (mirrors AuthService._store_refresh_token)."""
        token_hash = hash_refresh_token(raw_token)
        expires_at = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        await self._refresh_token_repo.create(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
