"""Cache layer: read-through with single-flight + observability (ROADMAP Epic 18).

The seam every cached feature goes through. It turns the bare ``AbstractCache``
(get/set/delete) into a read-through helper that:

* serves small, hot, shared reference data from an optional **in-process tier**
  in front of Redis, skipping the network round-trip entirely (opt-in per call
  via ``process_ttl_seconds``),
* collapses a stampede — N concurrent identical misses run **one** compute, the
  rest await it (in-process, per worker), and
* records per-namespace hit/miss counters so TTLs can be tuned against real
  hit-rates.

Everything stays best-effort: a cache outage degrades to a live compute, never
an error (the underlying ``AbstractCache`` swallows its own failures).
"""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict, defaultdict
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


# ── In-process tier (LRU + TTL, per worker) ──────────────────────────────


class _ProcessTier:
    """A tiny bounded LRU with per-entry TTL, in front of the shared cache.

    For small, hot, shared reference data (e.g. the platform list) this skips
    both the Redis round-trip and deserialisation. It holds live values, so use
    it only for immutable/JSON-safe data. Bounded by *maxsize* (oldest evicted);
    every entry self-expires, so a stale value never outlives its TTL.
    """

    def __init__(self, maxsize: int = 256) -> None:
        self._maxsize = maxsize
        self._entries: OrderedDict[str, tuple[float, Any]] = OrderedDict()

    def get(self, key: str) -> tuple[bool, Any]:
        entry = self._entries.get(key)
        if entry is None:
            return False, None
        expires_at, value = entry
        if expires_at <= time.monotonic():
            self._entries.pop(key, None)
            return False, None
        self._entries.move_to_end(key)
        return True, value

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        self._entries[key] = (time.monotonic() + ttl_seconds, value)
        self._entries.move_to_end(key)
        while len(self._entries) > self._maxsize:
            self._entries.popitem(last=False)

    def clear(self) -> None:
        self._entries.clear()


process_tier = _ProcessTier()


# ── Observability ────────────────────────────────────────────────────────

_counters: dict[str, dict[str, int]] = defaultdict(lambda: {"hit": 0, "miss": 0})


def _record(namespace: str, *, hit: bool) -> None:
    _counters[namespace]["hit" if hit else "miss"] += 1


def cache_stats() -> dict[str, dict[str, int]]:
    """Snapshot of per-namespace hit/miss counters."""
    return {ns: dict(counts) for ns, counts in _counters.items()}


def reset_cache_stats() -> None:
    """Clear the counters and the in-process tier (used by tests)."""
    _counters.clear()
    process_tier.clear()


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
    process_ttl_seconds: int | None = None,
) -> T:
    """Return a cached value for *key*, computing + storing it on a miss.

    *loads*/*dumps* convert between the live value (e.g. a Pydantic model) and a
    JSON-able cache payload; omit them when the value is already JSON-able.
    *cache_if* gates whether a freshly computed value is stored — use it to skip
    caching degraded results (e.g. a deep recap that fell back to quick). Set
    *skip_cache* to force a fresh compute where freshness must be guaranteed.
    *process_ttl_seconds* opts the key into the in-process tier in front of the
    shared cache — only for small, hot, immutable/JSON-safe reference data.
    """
    if skip_cache:
        return await compute()

    tiered = process_ttl_seconds is not None
    if tiered:
        hit, value = process_tier.get(key)
        if hit:
            _record(namespace, hit=True)
            return value  # type: ignore[no-any-return]

    def _promote(value: T) -> T:
        if tiered:
            process_tier.set(key, value, process_ttl_seconds)  # type: ignore[arg-type]
        return value

    cached = await cache.get_json(key)
    if cached is not None:
        _record(namespace, hit=True)
        return _promote(loads(cached) if loads else cached)

    # Miss: serialise concurrent identical misses so only the leader computes.
    async with single_flight(key):
        cached = await cache.get_json(key)
        if cached is not None:
            _record(namespace, hit=True)
            return _promote(loads(cached) if loads else cached)

        _record(namespace, hit=False)
        value = await compute()
        if cache_if is None or cache_if(value):
            await cache.set_json(key, dumps(value) if dumps else value, ttl_seconds)
        return _promote(value)
