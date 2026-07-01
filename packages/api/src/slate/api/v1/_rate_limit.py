"""Redis-backed rate limiting as a FastAPI dependency factory.

Built on ``pyrate_limiter``'s async ``RedisBucket`` over a shared
``redis.asyncio`` client (``settings.redis_url``). The Redis backend makes the
window shared across worker processes — the in-memory bucket counts per-process,
which is the bug this replaces.

``rate_limit(scope, times, seconds, by)`` returns a dependency that consumes one
permit from the bucket keyed by ``f"rl:{scope}:{identity}"`` and raises **429**
with a ``Retry-After`` header once the window is full. Identity is the
authenticated user (``by="user"``) or the client IP (``by="ip"``, uvicorn runs
with ``--proxy-headers``).

Fail-open by design: the limiter NEVER hard-fails a request. Any limiter/Redis
error allows the request (logged as a warning), so the API works without Redis.
When ``settings.rate_limit_enabled`` is False the dependency is a no-op (tests
and "limiter off" deploys). The per-key ``Limiter`` instances (and their Redis
Lua script load) are created lazily on first use, so importing this module and
starting the app never require Redis.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from inspect import isawaitable
from typing import Literal

import structlog
from fastapi import HTTPException, Request, status
from pyrate_limiter import Duration, Limiter, Rate, RedisBucket

from slate.deps.auth import CurrentUserDep
from slate.infrastructure.cache.redis_client import get_redis_client
from slate.infrastructure.config.dynamic import dynamic_config

logger = structlog.get_logger()

RateLimitBy = Literal["user", "ip"]

# One Limiter per (scope, times, seconds, identity). pyrate_limiter's RedisBucket
# counts the WHOLE bucket (Lua ZCOUNT over the ZSET), so the identity must live
# in the bucket key — not the per-item ``name`` — for windows to be isolated per
# user/IP. Memoised so the Lua script is loaded once per bucket, not per request.
_limiters: dict[str, Limiter] = {}


def _client_ip(request: Request) -> str:
    """Resolve the client IP (uvicorn runs with ``--proxy-headers``)."""
    return request.client.host if request.client else "unknown"


async def _get_limiter(scope: str, identity: str, times: int, seconds: int) -> Limiter:
    """Return (lazily building) the Redis-backed limiter for this key/rate."""
    cache_key = f"{scope}:{times}:{seconds}:{identity}"
    limiter = _limiters.get(cache_key)
    if limiter is None:
        rate = Rate(times, Duration.SECOND * seconds)
        bucket = await RedisBucket.init(
            [rate], get_redis_client(), bucket_key=f"rl:{scope}:{identity}"
        )
        limiter = Limiter(bucket)
        _limiters[cache_key] = limiter
    return limiter


async def _enforce(
    scope: str,
    identity: str,
    times: int,
    seconds: int,
    fail_closed: bool = False,
) -> None:
    """Consume one permit; raise 429 when the window is full.

    Fail mode on a limiter/Redis error:

    - ``fail_closed=False`` (default): allow the request (logged as a warning) —
      the limiter never hard-fails a request.
    - ``fail_closed=True``: **deny** with 503 — used on account-minting/auth
      routes where silently losing the limiter is unacceptable.

    The bucket key embeds the identity so each user/IP gets its own window.
    """
    try:
        limiter = await _get_limiter(scope, identity, times, seconds)
        # The async RedisBucket makes try_acquire awaitable; the signature is a
        # sync/async union, so resolve it defensively.
        result = limiter.try_acquire(scope, blocking=False)
        acquired = await result if isawaitable(result) else result
    except Exception:
        logger.warning(
            "rate_limit_redis_error", scope=scope, fail_closed=fail_closed, exc_info=True
        )
        if fail_closed:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Rate limiter unavailable. Please try again shortly.",
                headers={"Retry-After": str(seconds)},
            ) from None
        return

    if not acquired:
        logger.warning(
            "rate_limit_exceeded",
            scope=scope,
            identity=identity,
            limit=times,
            window_seconds=seconds,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please slow down.",
            headers={"Retry-After": str(seconds)},
        )


def rate_limit(
    scope: str,
    times: int,
    seconds: int,
    by: RateLimitBy = "user",
    fail_closed: bool = False,
    times_key: str | None = None,
) -> Callable[..., Awaitable[None]]:
    """Build a FastAPI dependency enforcing ``times`` requests per ``seconds``.

    ``scope`` namespaces the bucket (one scope per protected route). ``by``
    selects the identity: the authenticated user id (``"user"``) or the client
    IP (``"ip"``). When ``fail_closed`` is True a limiter/Redis error denies the
    request (503) instead of allowing it — use for account-minting/auth routes.

    Both the master switch (``rate_limit_enabled``) and — when ``times_key`` names
    a curated config key — the per-window allowance are resolved from the dynamic
    overlay at request time, so an admin can flip the limiter or retune the cap
    live without a redeploy. The returned dependency is a no-op when rate limiting
    is disabled, regardless of ``fail_closed``.
    """

    async def _resolve_times() -> int:
        return await dynamic_config.get_int(times_key) if times_key else times

    if by == "user":

        async def _dep_user(current_user: CurrentUserDep) -> None:
            if not await dynamic_config.get_bool("rate_limit_enabled"):
                return
            await _enforce(
                scope, str(current_user.id), await _resolve_times(), seconds, fail_closed
            )

        return _dep_user

    async def _dep_ip(request: Request) -> None:
        if not await dynamic_config.get_bool("rate_limit_enabled"):
            return
        await _enforce(scope, _client_ip(request), await _resolve_times(), seconds, fail_closed)

    return _dep_ip


# ---------------------------------------------------------------------------
# Per-ACCOUNT limiting — complements the per-IP limiter on the pre-auth routes.
# A distributed attacker rotating source IPs (no spoofing needed) otherwise gets
# a full per-IP allowance against a SINGLE victim account; keying a second bucket
# on the target account (submitted email / challenge subject) caps that.
# ---------------------------------------------------------------------------

BodyIdentity = Callable[[Request], Awaitable[str | None]]


async def account_email_identity(request: Request) -> str | None:
    """Return a normalized ``email:<addr>`` identity from the JSON body, or None."""
    try:
        body = await request.json()
    except Exception:
        return None
    email = body.get("email") if isinstance(body, dict) else None
    if isinstance(email, str) and email.strip():
        return f"email:{email.strip().lower()}"
    return None


def account_rate_limit(
    scope: str,
    times: int,
    seconds: int,
    extract: BodyIdentity,
    *,
    fail_closed: bool = True,
    times_key: str | None = None,
) -> Callable[..., Awaitable[None]]:
    """Build a dependency that rate-limits by the TARGET ACCOUNT, not the IP.

    *extract* pulls the account identity from the request body (the submitted
    email, or a challenge subject). When it returns None (body unparsable /
    field absent) the account axis is skipped — the handler's own validation and
    the per-IP limiter still apply, so a malformed request isn't given a free
    pass but also isn't double-counted on a bogus key.
    """

    async def _dep(request: Request) -> None:
        if not await dynamic_config.get_bool("rate_limit_enabled"):
            return
        identity = await extract(request)
        if identity is None:
            return
        resolved = await dynamic_config.get_int(times_key) if times_key else times
        await _enforce(scope, identity, resolved, seconds, fail_closed)

    return _dep
