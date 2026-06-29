"""Cache layer: read-through with single-flight + observability (ROADMAP Epic 18).

The seam every cached feature goes through. It turns the bare ``AbstractCache``
(get/set/delete) into a read-through helper that:

* collapses a stampede — N concurrent identical misses run **one** compute, the
  rest await it (in-process, per worker), and
* records per-namespace hit/miss counters so TTLs can be tuned against real
  hit-rates.

Everything stays best-effort: a cache outage degrades to a live compute, never
an error (the underlying ``AbstractCache`` swallows its own failures).
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from .base import AbstractCache

# ── Single-flight registry (in-process) ──────────────────────────────────


class _SingleFlight:
    """Per-key async lock with refcounted cleanup, so the map stays bounded."""

    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}
        self._refs: dict[str, int] = {}

    @asynccontextmanager
    async def __call__(self, key: str) -> Any:
        lock = self._locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[key] = lock
            self._refs[key] = 0
        self._refs[key] += 1
        try:
            async with lock:
                yield
        finally:
            self._refs[key] -= 1
            if self._refs[key] == 0:
                self._locks.pop(key, None)
                self._refs.pop(key, None)


single_flight = _SingleFlight()


# ── Observability ────────────────────────────────────────────────────────

_counters: dict[str, dict[str, int]] = defaultdict(lambda: {"hit": 0, "miss": 0})


def _record(namespace: str, *, hit: bool) -> None:
    _counters[namespace]["hit" if hit else "miss"] += 1


def cache_stats() -> dict[str, dict[str, int]]:
    """Snapshot of per-namespace hit/miss counters."""
    return {ns: dict(counts) for ns, counts in _counters.items()}


def reset_cache_stats() -> None:
    """Clear the counters (used by tests)."""
    _counters.clear()


# ── Read-through helper ──────────────────────────────────────────────────


async def cached_call[T](
    *,
    cache: AbstractCache,
    key: str,
    ttl_seconds: int,
    namespace: str,
    compute: Callable[[], Awaitable[T]],
    loads: Callable[[Any], T] | None = None,
    dumps: Callable[[T], Any] | None = None,
    cache_if: Callable[[T], bool] | None = None,
    skip_cache: bool = False,
) -> T:
    """Return a cached value for *key*, computing + storing it on a miss.

    *loads*/*dumps* convert between the live value (e.g. a Pydantic model) and a
    JSON-able cache payload; omit them when the value is already JSON-able.
    *cache_if* gates whether a freshly computed value is stored — use it to skip
    caching degraded results (e.g. a deep recap that fell back to quick). Set
    *skip_cache* to force a fresh compute where freshness must be guaranteed.
    """
    if skip_cache:
        return await compute()

    cached = await cache.get_json(key)
    if cached is not None:
        _record(namespace, hit=True)
        return loads(cached) if loads else cached

    # Miss: serialise concurrent identical misses so only the leader computes.
    async with single_flight(key):
        cached = await cache.get_json(key)
        if cached is not None:
            _record(namespace, hit=True)
            return loads(cached) if loads else cached

        _record(namespace, hit=False)
        value = await compute()
        if cache_if is None or cache_if(value):
            await cache.set_json(key, dumps(value) if dumps else value, ttl_seconds)
        return value
