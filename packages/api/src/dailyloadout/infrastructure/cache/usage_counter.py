"""Atomic Redis-backed rolling/window counters for cost + budget guards.

A single ``INCR`` (which returns the new value) plus a best-effort ``EXPIRE`` on
first hit gives a fixed-window counter that is shared across worker processes —
exactly what the cost kill-switch and the per-user IGDB budget need. The TTL is
(re)applied only when the counter is created (value == 1) so the window slides
forward one bucket at a time rather than being extended on every hit.

Two helpers:

- :func:`incr_window` — increment and return the new count. Raises on a Redis
  error so the *caller* decides fail-open vs fail-closed.
- :func:`peek_window` — read the current count without incrementing (for the
  pre-cap alert hook), returning 0 on any error.

Window keys embed a UTC time bucket (minute / day / month) so a fresh window
starts automatically at each boundary without a sweeper.
"""

from __future__ import annotations

from datetime import UTC, datetime

from dailyloadout.infrastructure.cache.redis_client import get_redis_client


def minute_bucket(now: datetime | None = None) -> str:
    """Return the current UTC minute bucket key fragment (``YYYYMMDDHHMM``)."""
    return (now or datetime.now(UTC)).strftime("%Y%m%d%H%M")


def day_bucket(now: datetime | None = None) -> str:
    """Return the current UTC day bucket key fragment (``YYYYMMDD``)."""
    return (now or datetime.now(UTC)).strftime("%Y%m%d")


def month_bucket(now: datetime | None = None) -> str:
    """Return the current UTC month bucket key fragment (``YYYYMM``)."""
    return (now or datetime.now(UTC)).strftime("%Y%m")


async def incr_window(key: str, ttl_seconds: int) -> int:
    """Atomically increment *key* and return the new count.

    Applies *ttl_seconds* only on the first increment (count == 1) so the window
    expires a fixed duration after it opened. Propagates Redis errors so the
    caller can choose its fail mode.
    """
    client = get_redis_client()
    count = await client.incr(key)
    if count == 1:
        await client.expire(key, ttl_seconds)
    return int(count)


async def peek_window(key: str) -> int:
    """Return the current count for *key* (0 if unset or on any error)."""
    try:
        client = get_redis_client()
        value = await client.get(key)
    except Exception:
        return 0
    return int(value) if value is not None else 0
