"""Repository for per-user, per-day usage counters (ROADMAP Epic 14)."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dailyloadout.infrastructure.db.models import UsageCounter


class UsageCounterRepository:
    """Read and increment daily usage counters."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _get(self, user_id: int, key: str, day: date) -> UsageCounter | None:
        stmt = select(UsageCounter).where(
            UsageCounter.user_id == user_id,
            UsageCounter.key == key,
            UsageCounter.day == day,
        )
        counter: UsageCounter | None = await self._session.scalar(stmt)
        return counter

    async def get_count(self, user_id: int, key: str, day: date) -> int:
        """Return the current count for (user, key, day), or 0 if unset."""
        counter = await self._get(user_id, key, day)
        return counter.count if counter is not None else 0

    async def increment(self, user_id: int, key: str, day: date, amount: int = 1) -> int:
        """Add *amount* to (user, key, day) and return the new total.

        Get-or-create within the request transaction — portable across Postgres
        and the SQLite test DB. The unique constraint on (user_id, key, day) is
        the backstop against concurrent double-inserts.
        """
        counter = await self._get(user_id, key, day)
        if counter is None:
            counter = UsageCounter(user_id=user_id, key=key, day=day, count=amount)
            self._session.add(counter)
        else:
            counter.count += amount
        await self._session.flush()
        return counter.count
