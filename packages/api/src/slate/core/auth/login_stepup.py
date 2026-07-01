"""Login step-up: require a CAPTCHA after N failed attempts on an account.

**Not a lockout** — locking an account out is a DoS vector (an attacker could lock
a victim out on purpose). Instead, after a burst of failures on one email, the next
login must solve a Turnstile challenge: automated credential-stuffing on a known
account is throttled while a real user just clicks a box. It complements the
per-account rate limit (which bounds the *rate*) by bounding *sustained* guessing.

Backed by a Redis counter, **best-effort**: any Redis error degrades to "no
step-up" (fail-open) — never a locked-out user or a 500 on the login path.
"""

from __future__ import annotations

import contextlib

from slate.config import settings
from slate.infrastructure.cache.redis_client import get_redis_client


def _key(email: str) -> str:
    return f"login_fail:{email.strip().lower()}"


async def login_stepup_required(email: str) -> bool:
    """True if *email* has hit the failed-attempt threshold (→ require CAPTCHA)."""
    with contextlib.suppress(Exception):
        raw = await get_redis_client().get(_key(email))
        return int(raw or 0) >= settings.login_stepup_after_failures
    return False


async def record_login_failure(email: str) -> None:
    """Count a failed login for *email* (first failure starts the window TTL)."""
    with contextlib.suppress(Exception):
        redis = get_redis_client()
        key = _key(email)
        if await redis.incr(key) == 1:
            await redis.expire(key, settings.login_stepup_window_seconds)


async def reset_login_failures(email: str) -> None:
    """Clear the failure counter after a successful login."""
    with contextlib.suppress(Exception):
        await get_redis_client().delete(_key(email))
