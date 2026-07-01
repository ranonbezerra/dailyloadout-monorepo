"""Server-side, single-use PKCE/state store for the OAuth flow (Redis-backed).

The ``state`` value is an unguessable token echoed by the provider on the
callback; we look it up here to (a) prove the callback corresponds to a request
WE started (CSRF defence) and (b) recover the matching ``code_verifier`` for the
PKCE token exchange. Entries are single-use (``GETDEL``) and expire after
``oauth_state_ttl_seconds`` so a leaked/replayed state cannot be reused.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from slate.config import settings
from slate.infrastructure.cache.redis_client import get_redis_client

_KEY_PREFIX = "oauth:state:"


@dataclass(frozen=True)
class OAuthState:
    """The data stashed under a ``state`` between /start and /callback.

    ``nonce_hash`` is the SHA-256 of a per-flow nonce whose raw value is set as a
    cookie in the initiating browser at ``/start``. The callback requires the
    cookie's nonce to hash to this value, binding the callback to the browser
    that started the flow (anti login-CSRF / session-fixation).
    """

    provider: str
    code_verifier: str
    nonce_hash: str = ""


def hash_oauth_nonce(nonce: str) -> str:
    """SHA-256 hex of the browser-binding *nonce* (only the hash is stored server-side)."""
    return hashlib.sha256(nonce.encode()).hexdigest()


async def store_state(state: str, data: OAuthState) -> None:
    """Persist *data* under *state* with the configured single-use TTL."""
    client = get_redis_client()
    payload = json.dumps(
        {
            "provider": data.provider,
            "code_verifier": data.code_verifier,
            "nonce_hash": data.nonce_hash,
        }
    )
    await client.set(f"{_KEY_PREFIX}{state}", payload, ex=settings.oauth_state_ttl_seconds)


async def consume_state(state: str) -> OAuthState | None:
    """Atomically fetch-and-delete the entry for *state* (single use)."""
    client = get_redis_client()
    raw = await client.getdel(f"{_KEY_PREFIX}{state}")
    if raw is None:
        return None
    try:
        data = json.loads(raw)
        return OAuthState(
            provider=str(data["provider"]),
            code_verifier=str(data["code_verifier"]),
            nonce_hash=str(data.get("nonce_hash", "")),
        )
    except (ValueError, KeyError, TypeError):
        return None
