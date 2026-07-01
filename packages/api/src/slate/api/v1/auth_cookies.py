"""Refresh-cookie helpers for the web cookie-mode auth contract.

Web clients opt into httpOnly-cookie storage of the refresh token by sending
the ``X-Auth-Mode: cookie`` header on login/register/refresh/logout. When that
header is absent (the default — used by the Flutter app), the endpoints keep
the legacy BODY-mode behaviour and the refresh token travels in the JSON body.

CSRF note: the app/data endpoints all authenticate via the ``Authorization:
Bearer`` header (CSRF-immune — browsers do not auto-attach it). Only
``/v1/auth/refresh`` relies on the cookie, and it merely rotates the token.
With the SameSite default, the cookie is not sent on cross-site requests, so no
separate CSRF token is required for the lax/same-site setup.
"""

from __future__ import annotations

from fastapi import Request, Response

from slate.config import settings
from slate.core.auth.security import REFRESH_TOKEN_EXPIRE_DAYS

_COOKIE_MODE_HEADER = "X-Auth-Mode"
_COOKIE_MODE_VALUE = "cookie"
_REFRESH_COOKIE_MAX_AGE = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

# Short-lived cookie carrying the OAuth browser-binding nonce (raw; only its hash
# is stored server-side). SameSite=lax so it rides the top-level provider→callback
# redirect; scoped to the OAuth path.
OAUTH_NONCE_COOKIE = "slate_oauth_nonce"
_OAUTH_NONCE_PATH = "/v1/auth/oauth"


def is_cookie_mode(request: Request) -> bool:
    """Return ``True`` when the caller opted into cookie-mode auth."""
    return request.headers.get(_COOKIE_MODE_HEADER) == _COOKIE_MODE_VALUE


def set_refresh_cookie(response: Response, token: str) -> None:
    """Store *token* as the httpOnly refresh cookie."""
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path=settings.auth_cookie_path,
        domain=settings.auth_cookie_domain,
        max_age=_REFRESH_COOKIE_MAX_AGE,
    )


def clear_refresh_cookie(response: Response) -> None:
    """Delete the refresh cookie (same name/path/domain it was set with)."""
    response.delete_cookie(
        key=settings.auth_cookie_name,
        path=settings.auth_cookie_path,
        domain=settings.auth_cookie_domain,
    )


def read_refresh_cookie(request: Request) -> str | None:
    """Return the refresh token stored in the cookie, if present."""
    return request.cookies.get(settings.auth_cookie_name)


def set_oauth_nonce_cookie(response: Response, nonce: str) -> None:
    """Set the OAuth browser-binding nonce cookie for the duration of the flow."""
    response.set_cookie(
        key=OAUTH_NONCE_COOKIE,
        value=nonce,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path=_OAUTH_NONCE_PATH,
        max_age=settings.oauth_state_ttl_seconds,
    )


def read_oauth_nonce_cookie(request: Request) -> str | None:
    """Return the OAuth nonce from the cookie, if present."""
    return request.cookies.get(OAUTH_NONCE_COOKIE)


def clear_oauth_nonce_cookie(response: Response) -> None:
    """Delete the OAuth nonce cookie (same path it was set with)."""
    response.delete_cookie(key=OAUTH_NONCE_COOKIE, path=_OAUTH_NONCE_PATH)


__all__ = [
    "OAUTH_NONCE_COOKIE",
    "clear_oauth_nonce_cookie",
    "clear_refresh_cookie",
    "is_cookie_mode",
    "read_oauth_nonce_cookie",
    "read_refresh_cookie",
    "set_oauth_nonce_cookie",
    "set_refresh_cookie",
]
