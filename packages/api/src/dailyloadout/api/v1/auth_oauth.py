"""Social-login endpoints: Authorization-Code + PKCE start/callback (web).

``/start`` mints a PKCE pair + CSRF ``state`` (stashed server-side in Redis) and
redirects the browser to the provider. ``/callback`` validates the returned
state, exchanges the code, resolves/links/creates the user, then — for the web
cookie-mode contract — sets the httpOnly refresh cookie and redirects the
browser back to the SPA, which silent-refreshes to obtain an access token.

Apple and the native-app (body-mode) return are a follow-up (ROADMAP Epic 20).
"""

from __future__ import annotations

import secrets

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse

from dailyloadout.api.v1._rate_limit import rate_limit
from dailyloadout.api.v1.auth_cookies import set_refresh_cookie
from dailyloadout.config import settings
from dailyloadout.deps import AuthServiceDep
from dailyloadout.infrastructure.oauth import (
    OAuthAccountConflictError,
    OAuthError,
    OAuthState,
    build_authorize_url,
    build_provider,
    consume_state,
    exchange_code_for_user,
    generate_pkce_pair,
    store_state,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/v1/auth/oauth", tags=["auth"])

# Per-IP cap on flow starts (each mints a Redis state entry). Fail-open: a Redis
# hiccup must not block legitimate sign-in.
_check_oauth_start_rate = rate_limit(
    "auth_oauth_start", settings.rate_limit_login_per_minute, 60, by="ip"
)


def _callback_uri(provider: str) -> str:
    """The redirect_uri registered with the provider for *provider*."""
    return f"{settings.oauth_redirect_base_url}/v1/auth/oauth/{provider}/callback"


def _error_redirect(reason: str) -> RedirectResponse:
    """Redirect the browser to the web error page with a coarse *reason*."""
    return RedirectResponse(
        f"{settings.oauth_web_error_url}?error={reason}",
        status_code=status.HTTP_302_FOUND,
    )


@router.get("/{provider}/start", dependencies=[Depends(_check_oauth_start_rate)])
async def oauth_start(provider: str) -> RedirectResponse:
    """Begin the OAuth flow: redirect the browser to the provider."""
    config = build_provider(provider, settings)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OAuth provider not available",
        )

    verifier, challenge = generate_pkce_pair()
    state = secrets.token_urlsafe(32)
    await store_state(state, OAuthState(provider=provider, code_verifier=verifier))

    url = build_authorize_url(config, _callback_uri(provider), state, challenge)
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    state: str,
    code: str,
    auth_service: AuthServiceDep,
) -> RedirectResponse:
    """Complete the flow: validate state, resolve the user, issue our session."""
    state_data = await consume_state(state)
    if state_data is None or state_data.provider != provider:
        return _error_redirect("invalid_state")

    config = build_provider(provider, settings)
    if config is None:
        return _error_redirect("provider_unavailable")

    try:
        info = await exchange_code_for_user(
            config, code, state_data.code_verifier, _callback_uri(provider)
        )
        _user, _access, raw_refresh = await auth_service.oauth_resolve_user(provider, info)
    except OAuthAccountConflictError:
        return _error_redirect("account_exists")
    except (OAuthError, ValueError):
        logger.warning("oauth_callback_failed", provider=provider, exc_info=True)
        return _error_redirect("oauth_failed")

    # Web cookie-mode: set the refresh cookie on the redirect; the SPA mounts on
    # the success URL and silent-refreshes to get its access token.
    response = RedirectResponse(settings.oauth_web_success_url, status_code=status.HTTP_302_FOUND)
    set_refresh_cookie(response, raw_refresh)
    return response
