"""Auth service: registration, login, token refresh, logout."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from dailyloadout.core.auth.security import (
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from dailyloadout.infrastructure.db.models import User
from dailyloadout.infrastructure.db.repositories.refresh_token import RefreshTokenRepository
from dailyloadout.infrastructure.db.repositories.user import UserRepository


class AuthService:
    """Orchestrates registration, login, refresh, and logout flows."""

    def __init__(
        self,
        user_repo: UserRepository,
        refresh_token_repo: RefreshTokenRepository,
    ) -> None:
        self._user_repo = user_repo
        self._refresh_token_repo = refresh_token_repo

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
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
            ValueError: If *email* is already registered.
        """
        if await self._user_repo.email_exists(email):
            raise ValueError("Email already registered")

        pw_hash = hash_password(password)
        user = await self._user_repo.create(email, pw_hash, display_name)

        access_token = create_access_token(str(user.public_id))
        raw_refresh = generate_refresh_token()
        await self._store_refresh_token(user.id, raw_refresh)

        return user, access_token, raw_refresh

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------
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
            raise ValueError("Invalid credentials")

        if not verify_password(password, user.password_hash):
            raise ValueError("Invalid credentials")

        access_token = create_access_token(str(user.public_id))
        raw_refresh = generate_refresh_token()
        await self._store_refresh_token(user.id, raw_refresh, device_label=device_label)

        return user, access_token, raw_refresh

    # ------------------------------------------------------------------
    # Token refresh (rotation)
    # ------------------------------------------------------------------
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
            raise ValueError("Invalid or expired refresh token")

        # Revoke the old token (rotation)
        await self._refresh_token_repo.revoke(stored.id)

        # Fetch the owning user by internal id to get their public_id for the JWT
        user = await self._user_repo.get_by_id(stored.user_id)
        if user is None:
            raise ValueError("User not found")

        new_access = create_access_token(str(user.public_id))
        new_raw_refresh = generate_refresh_token()
        await self._store_refresh_token(
            stored.user_id,
            new_raw_refresh,
            device_label=stored.device_label,
        )

        return new_access, new_raw_refresh

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------
    async def logout(self, raw_refresh_token: str) -> None:
        """Revoke the refresh token identified by *raw_refresh_token*."""
        token_hash = hash_refresh_token(raw_refresh_token)
        stored = await self._refresh_token_repo.get_by_hash(token_hash)
        if stored is not None:
            await self._refresh_token_repo.revoke(stored.id)

    # ------------------------------------------------------------------
    # Current user lookup
    # ------------------------------------------------------------------
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
