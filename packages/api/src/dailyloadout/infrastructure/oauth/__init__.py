"""Social-login / OAuth infrastructure (Authorization Code + PKCE)."""

from __future__ import annotations

from dailyloadout.infrastructure.oauth.flow import (
    build_authorize_url,
    exchange_code_for_user,
    generate_pkce_pair,
)
from dailyloadout.infrastructure.oauth.providers import (
    SUPPORTED_PROVIDERS,
    OAuthAccountConflictError,
    OAuthError,
    OAuthProvider,
    OAuthUserInfo,
    build_provider,
    parse_userinfo,
)
from dailyloadout.infrastructure.oauth.state_store import (
    OAuthState,
    consume_state,
    store_state,
)

__all__ = [
    "SUPPORTED_PROVIDERS",
    "OAuthAccountConflictError",
    "OAuthError",
    "OAuthProvider",
    "OAuthState",
    "OAuthUserInfo",
    "build_authorize_url",
    "build_provider",
    "consume_state",
    "exchange_code_for_user",
    "generate_pkce_pair",
    "parse_userinfo",
    "store_state",
]
