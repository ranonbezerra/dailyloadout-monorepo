"""Social-login / OAuth infrastructure (Authorization Code + PKCE)."""

from __future__ import annotations

from slate.infrastructure.oauth.flow import (
    build_authorize_url,
    exchange_code_for_user,
    generate_pkce_pair,
)
from slate.infrastructure.oauth.providers import (
    SUPPORTED_PROVIDERS,
    OAuthAccountConflictError,
    OAuthError,
    OAuthProvider,
    OAuthUserInfo,
    build_provider,
    parse_userinfo,
)
from slate.infrastructure.oauth.state_store import (
    OAuthState,
    consume_state,
    hash_oauth_nonce,
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
    "hash_oauth_nonce",
    "parse_userinfo",
    "store_state",
]
