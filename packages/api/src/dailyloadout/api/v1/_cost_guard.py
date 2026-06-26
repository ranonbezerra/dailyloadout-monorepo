"""Global cost kill-switch as a FastAPI dependency (the #1 missing control).

Every LLM-bearing route consumes one permit from a set of Redis-backed counters
that approximate spend (one LLM request ≈ one unit of cost, provider-agnostic
until per-token Bedrock metering lands). When any ceiling is exceeded the request
is hard-failed with **503** before the expensive work runs:

- a **global rolling-minute** counter (burst protection across all users),
- a **global per-UTC-day** counter (daily budget cap),
- a **global per-UTC-month** counter (monthly budget cap), and
- a **per-user per-UTC-day** counter (one account can't drain the global cap).

Unlike the rate limiter this **fails closed**: a Redis error denies the request
(503) rather than allowing unbounded spend. It is a NO-OP when
``settings.cost_guard_enabled`` is False (tests + "guard off" deploys), which is
how the pytest env keeps the suite from 503-ing. It is independent of
``rate_limit_enabled``.

A metric/alert hook (``cost_alert``) is logged once usage crosses
``cost_alert_threshold`` of any ceiling, so an alert can fire *before* the cap.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import structlog
from fastapi import HTTPException, status

from dailyloadout.config import settings
from dailyloadout.deps.auth import CurrentUserDep
from dailyloadout.infrastructure.cache.usage_counter import (
    day_bucket,
    incr_window,
    minute_bucket,
    month_bucket,
)

logger = structlog.get_logger()

_DAY_SECONDS = 24 * 3600
_MONTH_SECONDS = 31 * _DAY_SECONDS


@dataclass(frozen=True)
class _Window:
    """One cost ceiling: its Redis key, the new count, the cap, and TTL."""

    name: str
    key: str
    ttl_seconds: int
    limit: int


def _windows(user_id: int, scope: str) -> list[_Window]:
    """Build the four cost windows checked on every cost-bearing request."""
    return [
        _Window(
            "global_minute",
            f"cost:g:min:{minute_bucket()}",
            60,
            settings.cost_global_per_minute,
        ),
        _Window(
            "global_day",
            f"cost:g:day:{day_bucket()}",
            _DAY_SECONDS,
            settings.cost_global_per_day,
        ),
        _Window(
            "global_month",
            f"cost:g:mon:{month_bucket()}",
            _MONTH_SECONDS,
            settings.cost_global_per_month,
        ),
        _Window(
            "user_day",
            f"cost:u:{user_id}:day:{day_bucket()}",
            _DAY_SECONDS,
            settings.cost_user_per_day,
        ),
    ]


def _maybe_alert(window: _Window, count: int, scope: str) -> None:
    """Log a pre-cap alert once usage crosses the configured threshold."""
    threshold = window.limit * settings.cost_alert_threshold
    if count >= threshold and count < window.limit:
        # Metric hook: emit a structured event a downstream alert can trigger on
        # before the hard cap is reached.
        logger.warning(
            "cost_guard_near_limit",
            window=window.name,
            scope=scope,
            count=count,
            limit=window.limit,
        )


async def _enforce(user_id: int, scope: str) -> None:
    """Consume one permit from each cost window; raise 503 over any ceiling.

    Fail-closed: any Redis error denies the request (503) so a broken counter
    never silently authorises unbounded spend.
    """
    try:
        for window in _windows(user_id, scope):
            count = await incr_window(window.key, window.ttl_seconds)
            _maybe_alert(window, count, scope)
            if count > window.limit:
                logger.warning(
                    "cost_guard_tripped",
                    window=window.name,
                    scope=scope,
                    count=count,
                    limit=window.limit,
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Service temporarily over capacity. Please try again later.",
                    headers={"Retry-After": "60"},
                )
    except HTTPException:
        raise
    except Exception:
        logger.warning("cost_guard_redis_error", scope=scope, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cost guard unavailable. Please try again shortly.",
            headers={"Retry-After": "60"},
        ) from None


def cost_guard(scope: str) -> Callable[..., Awaitable[None]]:
    """Build a FastAPI dependency enforcing the aggregate cost ceilings.

    ``scope`` names the cost-bearing surface (for logs/metrics only — all scopes
    share the same global + per-user counters, since the goal is an aggregate $
    cap, not a per-route quota).

    The returned dependency is a no-op when ``settings.cost_guard_enabled`` is
    False, independent of ``rate_limit_enabled``.
    """

    async def _dep(current_user: CurrentUserDep) -> None:
        if not settings.cost_guard_enabled:
            return
        await _enforce(current_user.id, scope)

    return _dep
