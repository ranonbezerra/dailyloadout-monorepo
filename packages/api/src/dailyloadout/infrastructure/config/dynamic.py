"""The dynamic-config overlay: ``override (Postgres) > env var > code default``.

A process-global accessor consumers call instead of reading ``settings``
directly for a curated key. On read it returns the runtime override from
``app_config`` when present, otherwise the ``settings`` baseline. Overrides are
cached in-process for a short TTL (one indexed read per key per TTL, not per
request); writes invalidate the key in the writing process, and other processes
pick up the change within the TTL — bounded, eventually-consistent staleness,
which the design explicitly accepts (Postgres stays the source of truth).

The overlay self-sources a DB session via a swappable factory so consumers never
have to thread one through (the rate-limit middleware and import-time limiters
have none). Only the *baseline* fallback is read live from ``settings`` each call
(never cached), so monkeypatching settings in tests still takes effect.
"""

from __future__ import annotations

import time
from typing import Final

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from dailyloadout.config import settings
from dailyloadout.infrastructure.config.registry import CONFIG_REGISTRY, ConfigKeySpec
from dailyloadout.infrastructure.db.repositories.app_config import AppConfigRepository
from dailyloadout.infrastructure.db.session import async_session_factory

_DEFAULT_TTL_SECONDS: Final = 15.0


class _Missing:
    """Sentinel: this key has no override row (distinct from a stored ``None``)."""


_MISSING: Final = _Missing()


class DynamicConfig:
    """Process-global overlay over ``settings`` for the curated keys."""

    def __init__(self, ttl_seconds: float = _DEFAULT_TTL_SECONDS) -> None:
        # key -> (override value or _MISSING, monotonic expiry)
        self._cache: dict[str, tuple[object, float]] = {}
        self._ttl = ttl_seconds
        # Swappable so tests can point the overlay at the test database.
        self._session_factory: async_sessionmaker[AsyncSession] = async_session_factory

    # ── Public API ──
    async def get_bool(self, key: str) -> bool:
        """Return the effective boolean value for a ``bool`` key."""
        spec = self._spec(key, "bool")
        value = await self._effective(spec)
        if not isinstance(value, bool):
            raise TypeError(f"{key!r} resolved to a non-bool value: {value!r}")
        return value

    async def get_int(self, key: str) -> int:
        """Return the effective integer value for an ``int`` key."""
        spec = self._spec(key, "int")
        value = await self._effective(spec)
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{key!r} resolved to a non-int value: {value!r}")
        return value

    def invalidate(self, key: str) -> None:
        """Drop *key* from the cache (write-through invalidation after a write)."""
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Drop the entire cache (used on shutdown and in tests)."""
        self._cache.clear()

    # ── Internals ──
    @staticmethod
    def _spec(key: str, kind: str) -> ConfigKeySpec:
        spec = CONFIG_REGISTRY.get(key)
        if spec is None:
            raise KeyError(f"Unknown dynamic-config key: {key!r}")
        if spec.kind != kind:
            raise TypeError(f"{key!r} is a {spec.kind} key, not {kind}")
        return spec

    async def _effective(self, spec: ConfigKeySpec) -> object:
        override = await self._lookup(spec.key)
        if override is _MISSING:
            return getattr(settings, spec.settings_attr)
        return override

    async def _lookup(self, key: str) -> object:
        """Return the cached/fresh override for *key* (or ``_MISSING``)."""
        cached = self._cache.get(key)
        if cached is not None and cached[1] > time.monotonic():
            return cached[0]
        async with self._session_factory() as session:
            row = await AppConfigRepository(session).get(key)
        value: object = row.value if row is not None else _MISSING
        self._cache[key] = (value, time.monotonic() + self._ttl)
        return value


# The single process-wide instance consumers import.
dynamic_config = DynamicConfig()
