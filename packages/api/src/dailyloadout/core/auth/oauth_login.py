"""Social-login resolution: map a provider identity to a user + our tokens.

Extracted from :class:`AuthService` to keep that file focused. The resolution
policy NEVER silently merges accounts — see :func:`resolve_oauth_login`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from dailyloadout.core.auth.security import (
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
)
from dailyloadout.core.sanitization import sanitize_display_name, validate_https_url
from dailyloadout.infrastructure.db.models import User
from dailyloadout.infrastructure.db.repositories.oauth import OAuthIdentityRepository
from dailyloadout.infrastructure.db.repositories.refresh_token import RefreshTokenRepository
from dailyloadout.infrastructure.db.repositories.user import UserRepository
from dailyloadout.infrastructure.oauth import (
    OAuthAccountConflictError,
    OAuthError,
    OAuthUserInfo,
)


async def resolve_oauth_login(
    *,
    user_repo: UserRepository,
    oauth_repo: OAuthIdentityRepository,
    rt_repo: RefreshTokenRepository,
    provider: str,
    info: OAuthUserInfo,
) -> tuple[User, str, str]:
    """Resolve a social identity to a user and issue our tokens.

    Resolution (never silently merges):
    1. Known ``(provider, provider_uid)`` → that user logs in.
    2. Otherwise the provider email decides:
       - **verified** + existing account → **link** (and mark it verified);
       - **verified** + no account → **create** a passwordless account;
       - **unverified** + existing account → **reject**
         (:class:`OAuthAccountConflictError`) — linking would enable takeover;
       - **unverified** + no account → **create** (still unverified, so the
         email-verify gate applies).

    Returns ``(user, access_token, raw_refresh_token)``.
    """
    identity = await oauth_repo.get_by_provider_uid(provider, info.provider_uid)
    if identity is not None:
        user = await user_repo.get_by_id(identity.user_id)
        if user is None:  # pragma: no cover - FK guarantees the row exists
            raise OAuthError("Linked account not found")
        return await _issue_session(rt_repo, user)

    if not info.email:
        # No identity and no email: cannot create (email is unique/NOT NULL)
        # nor safely link.
        raise OAuthError(f"{provider} did not provide an email")

    existing = await user_repo.get_by_email(info.email)
    if existing is not None:
        if not info.email_verified:
            raise OAuthAccountConflictError(
                "An account with this email already exists. Log in and link "
                "this provider from your settings."
            )
        await oauth_repo.create(existing.id, provider, info.provider_uid, info.email)
        if not existing.email_verified:
            await user_repo.set_email_verified(existing)
        return await _issue_session(rt_repo, existing)

    user = await user_repo.create_oauth_user(
        info.email,
        _safe_display_name(info.display_name),
        email_verified=info.email_verified,
        avatar_url=validate_https_url(info.avatar_url),
    )
    await oauth_repo.create(user.id, provider, info.provider_uid, info.email)
    return await _issue_session(rt_repo, user)


def _safe_display_name(value: str) -> str:
    """Sanitize a provider-supplied display name; fall back to ``"Player"``.

    OAuth display names are untrusted (the user controls their Google/Twitch
    profile). Run them through the same guard the password path uses, but never
    fail the whole login over a bad name — degrade to a safe default instead.
    """
    try:
        return sanitize_display_name(value)
    except ValueError:
        return "Player"


async def _issue_session(rt_repo: RefreshTokenRepository, user: User) -> tuple[User, str, str]:
    """Issue an access + refresh token pair for a social-login *user*."""
    access_token = create_access_token(str(user.public_id), user.token_version)
    raw_refresh = generate_refresh_token()
    expires_at = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    await rt_repo.create(
        user_id=user.id,
        token_hash=hash_refresh_token(raw_refresh),
        expires_at=expires_at,
    )
    return user, access_token, raw_refresh
