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

import math
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import structlog
from fastapi import HTTPException, status

from dailyloadout.config import settings
from dailyloadout.deps.auth import CurrentUserDep
from dailyloadout.infrastructure.cache.cost_fallback import incr_local_window
from dailyloadout.infrastructure.cache.usage_counter import (
    day_bucket,
    incr_window,
    minute_bucket,
    month_bucket,
)
from dailyloadout.infrastructure.config.dynamic import dynamic_config

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


async def _build_windows(user_id: int, scope: str) -> list[_Window]:
    """Build the four cost windows checked on every cost-bearing request.

    The two daily ceilings are read from the dynamic overlay so an admin can
    retighten them mid-incident without a redeploy; the minute/month windows
    stay on the env baseline.
    """
    cost_global_per_day = await dynamic_config.get_int("cost_global_per_day")
    cost_user_per_day = await dynamic_config.get_int("cost_user_per_day")
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
            cost_global_per_day,
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
            cost_user_per_day,
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


def _over_capacity() -> HTTPException:
    """The 503 raised when a cost ceiling is exceeded."""
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Service temporarily over capacity. Please try again later.",
        headers={"Retry-After": "60"},
    )


def _local_limit(window: _Window) -> int:
    """The per-process ceiling used in degraded mode.

    Global windows are divided by the configured worker count so the aggregate
    cap across all processes stays near the intended global limit; per-user
    windows are kept whole (they are already scoped to one account).
    """
    if not window.name.startswith("global_"):
        return window.limit
    workers = max(1, settings.cost_guard_fallback_workers)
    return max(1, math.ceil(window.limit / workers))


async def _enforce_redis(windows: list[_Window], scope: str) -> None:
    """Consume one permit from each Redis-backed window; raise 503 over a cap.

    Raises a non-``HTTPException`` (propagated to the caller) on any Redis
    error, so the caller can decide between degraded fallback and fail-closed.
    """
    for window in windows:
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
            raise _over_capacity()


def _enforce_local(windows: list[_Window], scope: str) -> None:
    """Degraded fallback: enforce the ceilings with per-process counters.

    Conservative and imprecise by design (per-process, lost on restart). Global
    caps are divided by the worker count; a breach still 503s, so spend stays
    bounded even with Redis down.
    """
    for window in windows:
        limit = _local_limit(window)
        count = incr_local_window(window.key, window.ttl_seconds)
        if count > limit:
            logger.warning(
                "cost_guard_tripped_degraded",
                window=window.name,
                scope=scope,
                count=count,
                limit=limit,
            )
            raise _over_capacity()


async def _enforce(user_id: int, scope: str) -> None:
    """Consume one permit from each cost window; raise 503 over any ceiling.

    On a Redis error the guard either degrades to per-process counters
    (``cost_guard_degraded_fallback_enabled``, the default — Redis is not a
    single point of failure) or fails closed with 503 (strict mode). Either way
    a broken counter never silently authorises unbounded spend.
    """
    windows = await _build_windows(user_id, scope)
    try:
        await _enforce_redis(windows, scope)
    except HTTPException:
        raise
    except Exception:
        if not settings.cost_guard_degraded_fallback_enabled:
            logger.warning("cost_guard_redis_error", scope=scope, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cost guard unavailable. Please try again shortly.",
                headers={"Retry-After": "60"},
            ) from None
        logger.warning("cost_guard_redis_degraded", scope=scope, exc_info=True)
        _enforce_local(windows, scope)


def cost_guard(scope: str) -> Callable[..., Awaitable[None]]:
    """Build a FastAPI dependency enforcing the aggregate cost ceilings.

    ``scope`` names the cost-bearing surface (for logs/metrics only — all scopes
    share the same global + per-user counters, since the goal is an aggregate $
    cap, not a per-route quota).

    The returned dependency is a no-op when ``settings.cost_guard_enabled`` is
    False, independent of ``rate_limit_enabled``.
    """

    async def _dep(current_user: CurrentUserDep) -> None:
        if not await dynamic_config.get_bool("cost_guard_enabled"):
            return
        await _enforce(current_user.id, scope)

    return _dep
