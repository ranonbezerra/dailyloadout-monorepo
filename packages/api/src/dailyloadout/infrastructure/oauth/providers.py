"""Social-login provider definitions (Google, Twitch) + userinfo parsing.

Each provider is a small immutable config (endpoints + scopes + credentials)
built from settings — a provider is "available" only when its client id is set.
``parse_userinfo`` normalises each provider's distinct userinfo payload into a
single :class:`OAuthUserInfo`. Apple and the native-app flows are split into a
follow-up epic (see ROADMAP Epic 20); this module covers Authorization-Code +
PKCE web providers only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dailyloadout.config import Settings

GOOGLE = "google"
TWITCH = "twitch"
SUPPORTED_PROVIDERS = (GOOGLE, TWITCH)

# Provider endpoints (module constants so the kwargs below aren't flagged as
# hardcoded secrets by the linter, mirroring the IGDB client).
_GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
_TWITCH_AUTHORIZE_URL = "https://id.twitch.tv/oauth2/authorize"
_TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
_TWITCH_USERINFO_URL = "https://api.twitch.tv/helix/users"


class OAuthError(Exception):
    """A provider/flow failure (token exchange, userinfo, bad state)."""


class OAuthAccountConflictError(Exception):
    """An UNVERIFIED provider email collides with an existing account.

    Linking would be an account-takeover vector, so the flow is rejected and
    the user is told to log in with their password and link in settings.
    """


@dataclass(frozen=True)
class OAuthUserInfo:
    """Normalised identity claims resolved from a provider."""

    provider_uid: str
    email: str | None
    email_verified: bool
    display_name: str
    avatar_url: str | None


@dataclass(frozen=True)
class OAuthProvider:
    """Immutable endpoint/scope/credential config for one provider."""

    name: str
    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    userinfo_url: str
    scopes: tuple[str, ...]


def build_provider(name: str, settings: Settings) -> OAuthProvider | None:
    """Return a configured provider, or ``None`` if unsupported/unconfigured."""
    if name == GOOGLE and settings.google_oauth_client_id:
        return OAuthProvider(
            name=GOOGLE,
            client_id=settings.google_oauth_client_id,
            client_secret=settings.google_oauth_client_secret,
            authorize_url=_GOOGLE_AUTHORIZE_URL,
            token_url=_GOOGLE_TOKEN_URL,
            userinfo_url=_GOOGLE_USERINFO_URL,
            scopes=("openid", "email", "profile"),
        )
    if name == TWITCH and settings.twitch_oauth_client_id:
        return OAuthProvider(
            name=TWITCH,
            client_id=settings.twitch_oauth_client_id,
            client_secret=settings.twitch_oauth_client_secret,
            authorize_url=_TWITCH_AUTHORIZE_URL,
            token_url=_TWITCH_TOKEN_URL,
            userinfo_url=_TWITCH_USERINFO_URL,
            scopes=("user:read:email",),
        )
    return None


def parse_userinfo(provider: str, payload: dict[str, Any]) -> OAuthUserInfo:
    """Map a provider's userinfo JSON into :class:`OAuthUserInfo`."""
    if provider == GOOGLE:
        return _parse_google(payload)
    if provider == TWITCH:
        return _parse_twitch(payload)
    raise OAuthError(f"Unknown provider: {provider}")


def _parse_google(payload: dict[str, Any]) -> OAuthUserInfo:
    """Google OIDC userinfo: ``sub``, ``email``, ``email_verified``, ``name``."""
    sub = payload.get("sub")
    if not sub:
        raise OAuthError("Google userinfo missing subject")
    email = payload.get("email")
    return OAuthUserInfo(
        provider_uid=str(sub),
        email=str(email) if email else None,
        email_verified=bool(payload.get("email_verified", False)),
        display_name=str(payload.get("name") or email or "Player"),
        avatar_url=_opt_str(payload.get("picture")),
    )


def _parse_twitch(payload: dict[str, Any]) -> OAuthUserInfo:
    """Twitch Helix ``GET /users``: a ``data`` list with one user object.

    Twitch exposes ``email`` only for accounts with a verified email (and the
    ``user:read:email`` scope), so a present email is provider-verified.
    """
    data = payload.get("data") or []
    if not data:
        raise OAuthError("Twitch userinfo returned no user")
    user = data[0]
    uid = user.get("id")
    if not uid:
        raise OAuthError("Twitch userinfo missing id")
    email = user.get("email")
    return OAuthUserInfo(
        provider_uid=str(uid),
        email=str(email) if email else None,
        email_verified=email is not None,
        display_name=str(user.get("display_name") or user.get("login") or "Player"),
        avatar_url=_opt_str(user.get("profile_image_url")),
    )


def _opt_str(value: Any) -> str | None:
    """Return ``value`` as a string, or ``None`` when falsy."""
    return str(value) if value else None
