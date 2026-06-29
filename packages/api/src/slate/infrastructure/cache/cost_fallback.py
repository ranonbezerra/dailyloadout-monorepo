"""In-process fixed-window counters: the cost guard's degraded fallback.

When Redis is unreachable the cost guard cannot do shared cross-worker
accounting. Rather than hard-503 every cost-bearing route (taking the LLM
features fully offline on a Redis blip), it drops to these per-process counters,
which bound spend conservatively — the *global* ceilings are divided by the
configured worker count (see ``_cost_guard``) so the aggregate across workers
stays near the intended cap.

Imprecise by design: counts are per-process and lost on restart, so this tier's
job is to *bound* burst spend, not to be exact. Sustained-cost protection in
degraded mode is the provider-side AWS Budgets backstop (ROADMAP Epic 14).

The store is a plain dict guarded by a lock and self-prunes expired entries, so
it can never grow unbounded even with a per-user key per active user.
"""

from __future__ import annotations

import threading
import time

# key -> (count, expiry_monotonic). Module-global => one store per worker
# process, which is exactly the granularity we want for the degraded fallback.
_counts: dict[str, tuple[int, float]] = {}
_lock = threading.Lock()

# Prune expired entries once the store crosses this many keys, so a burst of
# distinct per-user keys during an outage can't leak memory.
_PRUNE_THRESHOLD = 1024


def incr_local_window(key: str, ttl_seconds: int, *, now: float | None = None) -> int:
    """Atomically increment the in-process counter for *key*; return the count.

    A fixed window: the first hit seeds the count at 1 with an expiry
    ``now + ttl_seconds``; once expired the window resets to 1. Mirrors the
    Redis ``incr_window`` semantics (window slides, never extends) but lives
    only in this process.
    """
    current = time.monotonic() if now is None else now
    with _lock:
        if len(_counts) > _PRUNE_THRESHOLD:
            _prune_expired(current)
        entry = _counts.get(key)
        if entry is None or entry[1] <= current:
            _counts[key] = (1, current + ttl_seconds)
            return 1
        count = entry[0] + 1
        _counts[key] = (count, entry[1])
        return count


def _prune_expired(current: float) -> None:
    """Drop entries whose window has closed (caller holds ``_lock``)."""
    stale = [key for key, (_, expiry) in _counts.items() if expiry <= current]
    for key in stale:
        del _counts[key]


def reset_local_windows() -> None:
    """Clear every counter — test helper / explicit reset only."""
    with _lock:
        _counts.clear()
