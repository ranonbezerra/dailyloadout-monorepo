"""A tiny async cache port (ROADMAP Epic 17).

Just enough to cache JSON-serialisable values with a TTL. Keeps the Redis
dependency behind an interface so callers (e.g. the IGDB client) stay testable
with a fake, and so a missing/broken cache degrades to "no cache" rather than an
error.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AbstractCache(ABC):
    """Contract for a best-effort JSON cache."""

    @abstractmethod
    async def get_json(self, key: str) -> Any | None:
        """Return the cached value for *key*, or ``None`` on miss/unavailable."""
        ...

    @abstractmethod
    async def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        """Store *value* under *key* for *ttl_seconds*. Best-effort (never raises)."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Drop a single *key*. Best-effort (never raises)."""
        ...

    @abstractmethod
    async def delete_namespace(self, prefix: str) -> None:
        """Drop every key starting with *prefix*. Best-effort (never raises).

        The unit of invalidation: a user's stats live under ``stats:<id>:`` and
        are busted as a group on a play_session event. Implementations must scope the
        scan to *prefix* so one user's bust never touches another's keys.
        """
        ...


class NullCache(AbstractCache):
    """No-op cache: every read misses, every write is dropped."""

    async def get_json(self, key: str) -> Any | None:
        return None

    async def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        return None

    async def delete(self, key: str) -> None:
        return None

    async def delete_namespace(self, prefix: str) -> None:
        return None
