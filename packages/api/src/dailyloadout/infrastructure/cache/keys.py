"""Cache key + namespace conventions (ROADMAP Epic 18).

One place that builds every cache key, so the layout is consistent and — for
user-scoped data — *never* mixes two users into a shared key. Each namespace has
a stable prefix; user-scoped namespaces embed the ``user_id`` right after the
prefix so a whole user's slice can be invalidated with one ``delete_namespace``.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

# ── Namespace prefixes ───────────────────────────────────────────────────
# Keep the trailing separator out of the constant; builders add it.
NS_IGDB = "igdb"
NS_STATS = "stats"
NS_BRIEFING = "briefing"
NS_LLM = "llm"
NS_RESEARCH = "research"
NS_REF = "ref"


def _part(value: Any) -> str:
    """Render one key segment; ``None`` becomes a stable sentinel."""
    return "_" if value is None else str(value)


def digest(payload: Any) -> str:
    """Short stable hash of an arbitrary JSON-able payload.

    For content-addressed keys (identical inputs → identical key) where the raw
    value is too large or unsafe to embed in a key verbatim.
    """
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


# ── Stats (per-user) ─────────────────────────────────────────────────────


def stats_key(user_id: int, view: str, *params: Any) -> str:
    """Key for one stats *view* of a user, optionally parameterised.

    e.g. ``stats:42:heatmap:2026-01-01:2026-02-01`` — the ``user_id`` sits
    directly under the namespace so :func:`stats_namespace` busts them as a set.
    """
    base = f"{NS_STATS}:{user_id}:{view}"
    suffix = ":".join(_part(p) for p in params)
    return f"{base}:{suffix}" if suffix else base


def stats_namespace(user_id: int) -> str:
    """Prefix covering *all* of a user's stats keys — the invalidation unit."""
    return f"{NS_STATS}:{user_id}:"
