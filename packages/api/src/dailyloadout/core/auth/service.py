"""Auth service: registration, login, token refresh, logout."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog

from dailyloadout.config import settings
from dailyloadout.core.auth.oauth_login import resolve_oauth_login
from dailyloadout.core.auth.security import (
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    create_email_verification_token,
    decode_email_verification_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
    verify_password_dummy,
)
from dailyloadout.infrastructure.db.models import User
from dailyloadout.infrastructure.db.repositories.oauth import OAuthIdentityRepository
from dailyloadout.infrastructure.db.repositories.refresh_token import RefreshTokenRepository
from dailyloadout.infrastructure.db.repositories.user import UserRepository
from dailyloadout.infrastructure.email import Mailer, get_mailer, send_verification_email
from dailyloadout.infrastructure.email.validation import (
    EmailRejectedError,
    assert_email_acceptable,
)
from dailyloadout.infrastructure.oauth import OAuthError, OAuthUserInfo

logger = structlog.get_logger()

__all__ = ["AuthService", "EmailRejectedError"]


class AuthService:
    """Orchestrates registration, login, refresh, and logout flows."""

    def __init__(
        self,
        user_repo: UserRepository,
        refresh_token_repo: RefreshTokenRepository,
        mailer: Mailer | None = None,
        oauth_repo: OAuthIdentityRepository | None = None,
    ) -> None:
        self._user_repo = user_repo
        self._refresh_token_repo = refresh_token_repo
        self._mailer = mailer or get_mailer()
        self._oauth_repo = oauth_repo

    # ── Registration ──
    async def register(
        self,
        email: str,
        password: str,
        display_name: str,
    ) -> tuple[User, str, str]:
        """Create a new user and issue tokens.

        Returns:
            ``(user, access_token, raw_refresh_token)``

        Raises:
            EmailRejectedError: If the email is disposable or undeliverable.
            ValueError: If *email* is already registered.
        """
        # Identity-hygiene gates run FIRST and are purely domain/content-based,
        # so they reveal nothing about whether the account already exists.
        await assert_email_acceptable(email)

        if await self._user_repo.email_exists(email):
            raise ValueError("Email already registered")

        pw_hash = hash_password(password)

        # Dev/test auto-verify bypass: outside production, accounts are created
        # already verified and no email is sent, so local dev and the test suite
        # are never blocked by the verification gate.
        auto_verify = not settings.is_production
        user = await self._user_repo.create(
            email, pw_hash, display_name, email_verified=auto_verify
        )

        if not auto_verify:
            self._send_verification_email(user)

        access_token = create_access_token(str(user.public_id), user.token_version)
        raw_refresh = generate_refresh_token()
        await self._store_refresh_token(user.id, raw_refresh)

        return user, access_token, raw_refresh

    # ── Email verification ──
    async def verify_email(self, token: str) -> None:
        """Validate a verification *token* and mark the email verified.

        Idempotent: an already-verified user is a no-op success. An
        expired/invalid token or an unknown user raises ``ValueError``.
        """
        public_id_str = decode_email_verification_token(token)
        try:
            public_id = UUID(public_id_str)
        except ValueError as exc:
            raise ValueError("Invalid or expired verification token") from exc

        user = await self._user_repo.get_by_public_id(public_id)
        if user is None:
            raise ValueError("Invalid or expired verification token")

        if not user.email_verified:
            await self._user_repo.set_email_verified(user)

    async def resend_verification(self, email: str) -> None:
        """Best-effort re-send of a verification email.

        Neutral by design: it never reveals whether the email exists or is
        already verified — the caller always gets the same response.
        """
        user = await self._user_repo.get_by_email(email)
        if user is None or user.email_verified:
            return
        self._send_verification_email(user)

    def _send_verification_email(self, user: User) -> None:
        """Generate a verification token and best-effort send it via SMTP."""
        token = create_email_verification_token(str(user.public_id))
        send_verification_email(self._mailer, to=user.email, token=token)

    # ── Login ──
    async def login(
        self,
        email: str,
        password: str,
        device_label: str | None = None,
    ) -> tuple[User, str, str]:
        """Authenticate a user and issue tokens.

        Returns:
            ``(user, access_token, raw_refresh_token)``

        Raises:
            ValueError: If credentials are invalid.
        """
        user = await self._user_repo.get_by_email(email)
        if user is None or user.password_hash is None:
            # Constant-time: still run a bcrypt verification against a fixed
            # dummy hash so response time does not reveal account existence.
            verify_password_dummy(password)
            raise ValueError("Invalid credentials")

        if not verify_password(password, user.password_hash):
            raise ValueError("Invalid credentials")

        access_token = create_access_token(str(user.public_id), user.token_version)
        raw_refresh = generate_refresh_token()
        await self._store_refresh_token(user.id, raw_refresh, device_label=device_label)

        return user, access_token, raw_refresh

    # ── Social login (OAuth) — resolve/link/create, then issue our tokens ──
    async def oauth_resolve_user(
        self, provider: str, info: OAuthUserInfo
    ) -> tuple[User, str, str]:
        """Resolve a social identity to a user and issue our tokens.

        Delegates to :func:`resolve_oauth_login` (see it for the link/collision
        policy). Returns ``(user, access_token, raw_refresh_token)``.
        """
        if self._oauth_repo is None:  # pragma: no cover - wiring guard
            raise OAuthError("OAuth repository not configured")
        return await resolve_oauth_login(
            user_repo=self._user_repo,
            oauth_repo=self._oauth_repo,
            rt_repo=self._refresh_token_repo,
            provider=provider,
            info=info,
        )

    # ── Token refresh (rotation) ──
    async def refresh(self, raw_refresh_token: str) -> tuple[str, str]:
        """Rotate a refresh token and issue a new access token.

        Returns:
            ``(new_access_token, new_raw_refresh_token)``

        Raises:
            ValueError: If the token is invalid, expired, or revoked.
        """
        token_hash = hash_refresh_token(raw_refresh_token)
        stored = await self._refresh_token_repo.get_by_hash(token_hash)
        if stored is None:
            # Reuse detection: the active lookup missed, but if the hash exists at
            # all it means an already-rotated/revoked token was replayed — a theft
            # signal. Cut off the whole family (revoke all + bump token_version)
            # so the stolen token, and the legitimate one it was rotated from,
            # are both useless and the user is forced to re-login everywhere.
            replayed = await self._refresh_token_repo.get_any_by_hash(token_hash)
            if replayed is not None:
                logger.warning(
                    "refresh_token_reuse_detected",
                    user_id=replayed.user_id,
                    refresh_token_id=replayed.id,
                )
                await self._revoke_all_sessions_by_internal_id(replayed.user_id)
                # Persist the cutoff durably: the request raises below (→ 401),
                # which would otherwise roll back the security write.
                await self._refresh_token_repo.commit()
            raise ValueError("Invalid or expired refresh token")

        # Revoke the old token (rotation)
        await self._refresh_token_repo.revoke(stored.id)

        # Fetch the owning user by internal id to get their public_id for the JWT
        user = await self._user_repo.get_by_id(stored.user_id)
        if user is None:
            raise ValueError("User not found")

        new_access = create_access_token(str(user.public_id), user.token_version)
        new_raw_refresh = generate_refresh_token()
        await self._store_refresh_token(
            stored.user_id,
            new_raw_refresh,
            device_label=stored.device_label,
        )

        return new_access, new_raw_refresh

    # ── Logout ──
    async def logout(self, raw_refresh_token: str) -> None:
        """Revoke the refresh token identified by *raw_refresh_token*."""
        token_hash = hash_refresh_token(raw_refresh_token)
        stored = await self._refresh_token_repo.get_by_hash(token_hash)
        if stored is not None:
            await self._refresh_token_repo.revoke(stored.id)

    # ------------------------------------------------------------------
    # Session kill-switch (logout-everywhere) and incident response
    # ------------------------------------------------------------------
    async def revoke_all_sessions(self, user_id: int) -> None:
        """Cut off every session for *user_id* (internal id).

        Bumps ``token_version`` (instantly invalidating all outstanding access
        tokens) AND revokes all refresh tokens (killing every device). Used by
        logout-everywhere and as the building block for ban / theft response.
        """
        await self._revoke_all_sessions_by_internal_id(user_id)

    async def ban_user(self, user_id: int) -> None:
        """Suspend *user_id* (internal id) and fully cut off their access.

        Sets ``is_banned=True`` (so ``get_current_user`` 403s them), bumps
        ``token_version``, and revokes every refresh token — a complete cutoff.
        """
        await self._user_repo.set_banned(user_id, True)
        await self._revoke_all_sessions_by_internal_id(user_id)

    async def _revoke_all_sessions_by_internal_id(self, user_id: int) -> None:
        """Bump token_version and revoke all refresh tokens for *user_id*."""
        await self._user_repo.bump_token_version(user_id)
        await self._refresh_token_repo.revoke_all_for_user(user_id)

    # ── Current user lookup ──
    async def get_current_user(self, public_id: UUID) -> User:
        """Return the user with *public_id*.

        Raises:
            ValueError: If the user does not exist.
        """
        user = await self._user_repo.get_by_public_id(public_id)
        if user is None:
            raise ValueError("User not found")
        return user

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    async def _store_refresh_token(
        self,
        user_id: int,
        raw_token: str,
        device_label: str | None = None,
    ) -> None:
        """Hash *raw_token* and persist it in the database."""
        token_hash = hash_refresh_token(raw_token)
        expires_at = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        await self._refresh_token_repo.create(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            device_label=device_label,
        )
