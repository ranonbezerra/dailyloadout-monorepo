"""Repository for per-user, per-day usage counters (ROADMAP Epic 14)."""

from __future__ import annotations

from datetime import date

from sqlalchemy import ColumnElement, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Executable

from slate.infrastructure.db.models import UsageCounter

# Columns the unique constraint ``uq_usage_counters_user_key_day`` is built on.
_CONFLICT_COLS = ("user_id", "key", "day")


class UsageCounterRepository:
    """Read and atomically increment daily usage counters."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _upsert_returning(
        self,
        user_id: int,
        key: str,
        day: date,
        amount: int,
        *,
        where: ColumnElement[bool] | None = None,
    ) -> Executable:
        """Build a dialect-specific atomic upsert that returns the new count.

        ``INSERT ... ON CONFLICT (user_id, key, day) DO UPDATE
        SET count = count + :amount [WHERE ...] RETURNING count`` — Postgres and
        the SQLite test DB both support this construct, but it lives in separate
        dialect modules, so dispatch on ``bind.dialect.name``. The upsert and the
        read of the running total are one statement, closing the TOCTOU race.
        """
        bind = self._session.get_bind()
        values = {"user_id": user_id, "key": key, "day": day, "count": amount}
        new_count = UsageCounter.count + amount
        if bind.dialect.name == "postgresql":
            pg_stmt = pg_insert(UsageCounter).values(**values)
            return pg_stmt.on_conflict_do_update(
                index_elements=_CONFLICT_COLS,
                set_={"count": new_count},
                where=where,
            ).returning(UsageCounter.count)
        sqlite_stmt = sqlite_insert(UsageCounter).values(**values)
        return sqlite_stmt.on_conflict_do_update(
            index_elements=_CONFLICT_COLS,
            set_={"count": new_count},
            where=where,
        ).returning(UsageCounter.count)

    async def get_count(self, user_id: int, key: str, day: date) -> int:
        """Return the current count for (user, key, day), or 0 if unset."""
        stmt = select(UsageCounter.count).where(
            UsageCounter.user_id == user_id,
            UsageCounter.key == key,
            UsageCounter.day == day,
        )
        count: int | None = await self._session.scalar(stmt)
        return count if count is not None else 0

    async def increment(self, user_id: int, key: str, day: date, amount: int = 1) -> int:
        """Atomically add *amount* to (user, key, day) and return the new total.

        Single-statement upsert with no cap, so concurrent callers cannot
        read-modify-write over each other (the prior TOCTOU regression).
        """
        stmt = self._upsert_returning(user_id, key, day, amount)
        new_total: int | None = await self._session.scalar(stmt)
        await self._session.flush()
        assert new_total is not None  # unconditional upsert always returns a row
        return new_total

    async def increment_within_cap(
        self, user_id: int, key: str, day: date, amount: int, cap: int
    ) -> int | None:
        """Atomically increment only if the new total stays within *cap*.

        Returns the new running total when the increment is applied, or ``None``
        when applying it would exceed *cap* (in which case nothing is written,
        so a rejected request never over-counts or locks the user out — only
        successful consumption is recorded, matching the prior quota semantics).

        The cap is enforced *inside* the upsert via a conditional ``WHERE`` on
        the UPDATE, so two concurrent requests cannot both pass: the first to
        commit consumes the budget and the second's UPDATE matches no row,
        returning nothing.
        """
        # The conditional WHERE only guards the UPDATE (conflict) branch; a first
        # INSERT bypasses it, so reject an over-cap fresh row up front.
        if amount > cap:
            return None
        where = UsageCounter.count + amount <= cap
        stmt = self._upsert_returning(user_id, key, day, amount, where=where)
        new_total: int | None = await self._session.scalar(stmt)
        await self._session.flush()
        return new_total
