"""Unit tests for the cache layer (ROADMAP Epic 18).

Exercises the read-through helper, single-flight stampede protection, the
per-namespace counters, the key/namespace builders, and the user-stats
invalidation map — all with an in-memory fake cache (no Redis).
"""

from __future__ import annotations

import asyncio
from typing import Any

from slate.core.cache.invalidation import invalidate_user_stats
from slate.infrastructure.cache.keys import (
    digest,
    stats_key,
    stats_namespace,
)
from slate.infrastructure.cache.layer import (
    cache_stats,
    cached_call,
    reset_cache_stats,
)


class FakeCache:
    """In-memory AbstractCache for tests (ignores TTL)."""

    def __init__(self) -> None:
        self.store: dict[str, Any] = {}

    async def get_json(self, key: str) -> Any | None:
        return self.store.get(key)

    async def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        self.store[key] = value

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)

    async def delete_namespace(self, prefix: str) -> None:
        for key in [k for k in self.store if k.startswith(prefix)]:
            del self.store[key]


# ── Key builders ─────────────────────────────────────────────────────────


def test_stats_key_embeds_user_and_params() -> None:
    assert stats_key(42, "overview") == "stats:42:overview"
    assert stats_key(42, "heatmap", None, None) == "stats:42:heatmap:_:_"
    assert stats_key(7, "timeline", 20, 0) == "stats:7:timeline:20:0"


def test_stats_namespace_is_user_scoped() -> None:
    assert stats_namespace(42) == "stats:42:"
    # Every key for a user falls under their namespace prefix.
    assert stats_key(42, "overview").startswith(stats_namespace(42))
    # ...and never under a different user's namespace.
    assert not stats_key(42, "overview").startswith(stats_namespace(43))


def test_digest_is_stable_and_order_independent() -> None:
    assert digest({"a": 1, "b": 2}) == digest({"b": 2, "a": 1})
    assert digest({"a": 1}) != digest({"a": 2})


# ── Read-through + counters ──────────────────────────────────────────────


async def test_miss_then_hit_counts_correctly() -> None:
    reset_cache_stats()
    cache = FakeCache()
    calls = 0

    async def compute() -> dict[str, int]:
        nonlocal calls
        calls += 1
        return {"v": 1}

    first = await cached_call(cache=cache, key="k", ttl_seconds=10, namespace="t", compute=compute)
    second = await cached_call(
        cache=cache, key="k", ttl_seconds=10, namespace="t", compute=compute
    )

    assert first == second == {"v": 1}
    assert calls == 1  # second call served from cache
    assert cache_stats()["t"] == {"hit": 1, "miss": 1}


async def test_skip_cache_always_computes() -> None:
    cache = FakeCache()
    calls = 0

    async def compute() -> int:
        nonlocal calls
        calls += 1
        return calls

    a = await cached_call(
        cache=cache, key="k", ttl_seconds=10, namespace="t", compute=compute, skip_cache=True
    )
    b = await cached_call(
        cache=cache, key="k", ttl_seconds=10, namespace="t", compute=compute, skip_cache=True
    )
    assert (a, b) == (1, 2)
    assert "k" not in cache.store  # nothing was written


async def test_loads_dumps_round_trip() -> None:
    cache = FakeCache()

    async def compute() -> dict[str, int]:
        return {"n": 5}

    # Store a dumped form, reconstruct a tagged object on read.
    await cached_call(
        cache=cache,
        key="k",
        ttl_seconds=10,
        namespace="t",
        compute=compute,
        dumps=lambda v: {"wrapped": v},
    )
    assert cache.store["k"] == {"wrapped": {"n": 5}}

    out = await cached_call(
        cache=cache,
        key="k",
        ttl_seconds=10,
        namespace="t",
        compute=compute,
        loads=lambda raw: raw["wrapped"],
    )
    assert out == {"n": 5}


async def test_cache_if_skips_storing_rejected_values() -> None:
    cache = FakeCache()
    calls = 0

    async def compute() -> str:
        nonlocal calls
        calls += 1
        return ""  # an "empty"/degraded result we don't want to cache

    a = await cached_call(
        cache=cache, key="k", ttl_seconds=10, namespace="t", compute=compute, cache_if=bool
    )
    b = await cached_call(
        cache=cache, key="k", ttl_seconds=10, namespace="t", compute=compute, cache_if=bool
    )
    assert (a, b) == ("", "")
    assert calls == 2  # never stored, so the second call recomputes
    assert "k" not in cache.store


async def test_single_flight_collapses_concurrent_misses() -> None:
    cache = FakeCache()
    calls = 0
    release = asyncio.Event()

    async def compute() -> dict[str, int]:
        nonlocal calls
        calls += 1
        await release.wait()  # hold the leader so the others pile up
        return {"v": 1}

    async def run() -> dict[str, int]:
        return await cached_call(
            cache=cache, key="hot", ttl_seconds=10, namespace="t", compute=compute
        )

    tasks = [asyncio.create_task(run()) for _ in range(5)]
    await asyncio.sleep(0.01)  # let all five reach the single-flight gate
    release.set()
    results = await asyncio.gather(*tasks)

    assert calls == 1  # only the leader computed
    assert all(r == {"v": 1} for r in results)


# ── Invalidation ─────────────────────────────────────────────────────────


async def test_invalidate_user_stats_only_busts_that_user() -> None:
    cache = FakeCache()
    cache.store[stats_key(1, "overview")] = {"a": 1}
    cache.store[stats_key(1, "timeline", 20, 0)] = {"b": 2}
    cache.store[stats_key(2, "overview")] = {"c": 3}

    await invalidate_user_stats(1, cache=cache)

    # User 1's whole slice is gone; user 2 is untouched (no cross-user leak).
    assert stats_key(1, "overview") not in cache.store
    assert stats_key(1, "timeline", 20, 0) not in cache.store
    assert stats_key(2, "overview") in cache.store


async def test_invalidation_forces_recompute() -> None:
    cache = FakeCache()
    calls = 0

    async def compute() -> dict[str, int]:
        nonlocal calls
        calls += 1
        return {"n": calls}

    key = stats_key(1, "overview")
    a = await cached_call(cache=cache, key=key, ttl_seconds=10, namespace="stats", compute=compute)
    await invalidate_user_stats(1, cache=cache)
    b = await cached_call(cache=cache, key=key, ttl_seconds=10, namespace="stats", compute=compute)

    assert a == {"n": 1}
    assert b == {"n": 2}  # recomputed after the bust


# ── In-process tier (Epic 18) ────────────────────────────────────────────


class _CountingCache(FakeCache):
    """FakeCache that counts reads, to prove the tier skips the round-trip."""

    def __init__(self) -> None:
        super().__init__()
        self.reads = 0

    async def get_json(self, key: str) -> Any | None:
        self.reads += 1
        return await super().get_json(key)


async def test_process_tier_serves_repeat_without_touching_shared_cache() -> None:
    reset_cache_stats()
    cache = _CountingCache()
    calls = 0

    async def compute() -> dict[str, int]:
        nonlocal calls
        calls += 1
        return {"v": 1}

    kw = {"cache": cache, "key": "ref:x", "ttl_seconds": 10, "namespace": "ref"}
    first = await cached_call(compute=compute, process_ttl_seconds=60, **kw)  # type: ignore[arg-type]
    reads_after_first = cache.reads
    second = await cached_call(compute=compute, process_ttl_seconds=60, **kw)  # type: ignore[arg-type]

    assert first == second == {"v": 1}
    assert calls == 1  # computed once
    assert cache.reads == reads_after_first  # 2nd call from the tier, no shared-cache read
    assert cache_stats()["ref"] == {"hit": 1, "miss": 1}


async def test_process_tier_entry_expires_and_falls_back(monkeypatch: Any) -> None:
    reset_cache_stats()
    import slate.infrastructure.cache.layer as layer_mod

    clock = {"t": 1000.0}
    monkeypatch.setattr(layer_mod.time, "monotonic", lambda: clock["t"])

    cache = _CountingCache()

    async def compute() -> int:
        return 1

    kw = {"cache": cache, "key": "ref:y", "ttl_seconds": 999, "namespace": "ref"}
    await cached_call(compute=compute, process_ttl_seconds=5, **kw)  # type: ignore[arg-type]
    reads_after_first = cache.reads  # tier miss → shared-cache read(s)
    await cached_call(compute=compute, process_ttl_seconds=5, **kw)  # type: ignore[arg-type]
    assert cache.reads == reads_after_first  # within TTL: served from the tier

    clock["t"] += 6  # advance past the tier TTL
    await cached_call(compute=compute, process_ttl_seconds=5, **kw)  # type: ignore[arg-type]
    assert cache.reads > reads_after_first  # tier expired → shared cache consulted again


def test_process_tier_is_bounded_lru() -> None:
    from slate.infrastructure.cache.layer import _ProcessTier

    tier = _ProcessTier(maxsize=2)
    tier.set("a", 1, ttl_seconds=60)
    tier.set("b", 2, ttl_seconds=60)
    tier.get("a")  # touch "a" so "b" is the least-recently-used
    tier.set("c", 3, ttl_seconds=60)  # evicts the LRU ("b")

    assert tier.get("a") == (True, 1)
    assert tier.get("c") == (True, 3)
    assert tier.get("b") == (False, None)  # evicted
