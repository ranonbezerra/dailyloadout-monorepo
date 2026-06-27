"""OAuth Authorization-Code + PKCE flow helpers: URL build + token exchange.

PKCE (RFC 7636) defends the code: the ``code_verifier`` stays server-side (in
the Redis state entry) and only its S256 ``code_challenge`` rides the authorize
redirect, so an intercepted ``code`` is useless without the verifier.

``exchange_code_for_user`` does the two provider round-trips (code→token, then
token→userinfo) and returns normalised claims. Network/credential errors are
logged with status + path only (never the secret or query) and re-raised as a
clean :class:`OAuthError`.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from urllib.parse import urlencode

import httpx
import structlog

from dailyloadout.infrastructure.oauth.providers import (
    TWITCH,
    OAuthError,
    OAuthProvider,
    OAuthUserInfo,
    parse_userinfo,
)

logger = structlog.get_logger()

_HTTP_TIMEOUT = 10.0


def generate_pkce_pair() -> tuple[str, str]:
    """Return ``(code_verifier, code_challenge)`` for the S256 method."""
    verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def build_authorize_url(
    provider: OAuthProvider,
    redirect_uri: str,
    state: str,
    code_challenge: str,
) -> str:
    """Build the provider authorize URL the browser is redirected to."""
    params = {
        "client_id": provider.client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(provider.scopes),
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{provider.authorize_url}?{urlencode(params)}"


async def exchange_code_for_user(
    provider: OAuthProvider,
    code: str,
    code_verifier: str,
    redirect_uri: str,
) -> OAuthUserInfo:
    """Exchange *code* for an access token, then fetch + normalise userinfo."""
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        access_token = await _exchange_token(provider, client, code, code_verifier, redirect_uri)
        return await _fetch_userinfo(provider, client, access_token)


async def _exchange_token(
    provider: OAuthProvider,
    client: httpx.AsyncClient,
    code: str,
    code_verifier: str,
    redirect_uri: str,
) -> str:
    """POST the code→token exchange; return the access token."""
    resp = await client.post(
        provider.token_url,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": provider.client_id,
            "client_secret": provider.client_secret,
            "code_verifier": code_verifier,
        },
        headers={"Accept": "application/json"},
    )
    _raise_for_status(resp, provider.name, "token")
    token = resp.json().get("access_token")
    if not token:
        raise OAuthError(f"{provider.name} token response missing access_token")
    return str(token)


async def _fetch_userinfo(
    provider: OAuthProvider,
    client: httpx.AsyncClient,
    access_token: str,
) -> OAuthUserInfo:
    """GET the provider userinfo endpoint and normalise the payload."""
    headers = {"Authorization": f"Bearer {access_token}"}
    if provider.name == TWITCH:
        # Twitch Helix requires the app Client-Id alongside the user token.
        headers["Client-Id"] = provider.client_id
    resp = await client.get(provider.userinfo_url, headers=headers)
    _raise_for_status(resp, provider.name, "userinfo")
    return parse_userinfo(provider.name, resp.json())


def _raise_for_status(resp: httpx.Response, provider: str, stage: str) -> None:
    """Re-raise a provider HTTP error as a clean, secret-free ``OAuthError``."""
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "oauth_request_failed",
            provider=provider,
            stage=stage,
            status_code=exc.response.status_code,
            url=str(exc.request.url.copy_with(query=None)),
        )
        raise OAuthError(f"{provider} {stage} request failed") from None
