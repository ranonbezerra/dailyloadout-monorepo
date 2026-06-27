"""Server-side, single-use PKCE/state store for the OAuth flow (Redis-backed).

The ``state`` value is an unguessable token echoed by the provider on the
callback; we look it up here to (a) prove the callback corresponds to a request
WE started (CSRF defence) and (b) recover the matching ``code_verifier`` for the
PKCE token exchange. Entries are single-use (``GETDEL``) and expire after
``oauth_state_ttl_seconds`` so a leaked/replayed state cannot be reused.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from dailyloadout.config import settings
from dailyloadout.infrastructure.cache.redis_client import get_redis_client

_KEY_PREFIX = "oauth:state:"


@dataclass(frozen=True)
class OAuthState:
    """The data stashed under a ``state`` between /start and /callback."""

    provider: str
    code_verifier: str


async def store_state(state: str, data: OAuthState) -> None:
    """Persist *data* under *state* with the configured single-use TTL."""
    client = get_redis_client()
    payload = json.dumps({"provider": data.provider, "code_verifier": data.code_verifier})
    await client.set(f"{_KEY_PREFIX}{state}", payload, ex=settings.oauth_state_ttl_seconds)


async def consume_state(state: str) -> OAuthState | None:
    """Atomically fetch-and-delete the entry for *state* (single use)."""
    client = get_redis_client()
    raw = await client.getdel(f"{_KEY_PREFIX}{state}")
    if raw is None:
        return None
    try:
        data = json.loads(raw)
        return OAuthState(provider=str(data["provider"]), code_verifier=str(data["code_verifier"]))
    except (ValueError, KeyError, TypeError):
        return None
