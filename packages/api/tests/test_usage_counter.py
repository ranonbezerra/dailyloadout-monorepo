"""Tests for the atomic usage-counter repository (anti-abuse TOCTOU fix).

The increment is a single upsert (``INSERT ... ON CONFLICT DO UPDATE
... RETURNING count``) so concurrent callers cannot read the same pre-increment
count and overshoot a per-day cap. These tests assert the happy path is
unchanged and that the cap holds under concurrent increments.
"""

from __future__ import annotations

import asyncio
from datetime import date
from uuid import uuid4

from dailyloadout.infrastructure.db.models import User
from dailyloadout.infrastructure.db.repositories.usage import UsageCounterRepository

from .conftest import _TestSessionFactory

DAY = date(2026, 6, 24)
KEY = "library_import_images"


async def _seed_user(session: object) -> int:
    user = User(email=f"{uuid4().hex}@test.com", password_hash="h", display_name="T")
    session.add(user)  # type: ignore[attr-defined]
    await session.flush()  # type: ignore[attr-defined]
    return user.id


async def test_increment_creates_and_accumulates() -> None:
    async with _TestSessionFactory() as session:
        user_id = await _seed_user(session)
        repo = UsageCounterRepository(session)

        assert await repo.increment(user_id, KEY, DAY, amount=3) == 3
        assert await repo.increment(user_id, KEY, DAY) == 4
        assert await repo.get_count(user_id, KEY, DAY) == 4
        # A different day is tracked separately.
        assert await repo.get_count(user_id, KEY, date(2026, 6, 25)) == 0


async def test_increment_within_cap_allows_under_cap() -> None:
    async with _TestSessionFactory() as session:
        user_id = await _seed_user(session)
        repo = UsageCounterRepository(session)

        assert await repo.increment_within_cap(user_id, KEY, DAY, amount=4, cap=10) == 4
        assert await repo.increment_within_cap(user_id, KEY, DAY, amount=6, cap=10) == 10


async def test_increment_within_cap_rejects_over_cap_without_writing() -> None:
    async with _TestSessionFactory() as session:
        user_id = await _seed_user(session)
        repo = UsageCounterRepository(session)

        assert await repo.increment_within_cap(user_id, KEY, DAY, amount=8, cap=10) == 8
        # Would push the total to 12 > 10: rejected, and nothing is written.
        assert await repo.increment_within_cap(user_id, KEY, DAY, amount=4, cap=10) is None
        assert await repo.get_count(user_id, KEY, DAY) == 8
        # The user is not locked out: a smaller request that fits still passes.
        assert await repo.increment_within_cap(user_id, KEY, DAY, amount=2, cap=10) == 10


async def test_increment_within_cap_rejects_fresh_row_over_cap() -> None:
    """A first insert whose amount alone exceeds the cap is rejected, no row."""
    async with _TestSessionFactory() as session:
        user_id = await _seed_user(session)
        repo = UsageCounterRepository(session)

        assert await repo.increment_within_cap(user_id, KEY, DAY, amount=11, cap=10) is None
        assert await repo.get_count(user_id, KEY, DAY) == 0


async def test_concurrent_increments_hold_the_cap() -> None:
    """N concurrent increment_within_cap calls must never exceed the cap.

    Each task uses its own session/transaction so they genuinely contend on the
    same (user, key, day) row. The granted totals must be strictly monotonic and
    the final stored count must equal the cap exactly — the TOCTOU regression
    test: with the old read-modify-write all 20 would have read 0 and overshot.
    """
    cap = 10
    requests = 20

    async with _TestSessionFactory() as session:
        user_id = await _seed_user(session)
        await session.commit()

    async def claim() -> int | None:
        async with _TestSessionFactory() as session:
            repo = UsageCounterRepository(session)
            total = await repo.increment_within_cap(user_id, KEY, DAY, amount=1, cap=cap)
            await session.commit()
            return total

    results = await asyncio.gather(*(claim() for _ in range(requests)))

    granted = sorted(t for t in results if t is not None)
    rejected = [t for t in results if t is None]

    # Exactly *cap* requests were granted, each a distinct running total 1..cap.
    assert granted == list(range(1, cap + 1))
    assert len(rejected) == requests - cap

    async with _TestSessionFactory() as session:
        repo = UsageCounterRepository(session)
        assert await repo.get_count(user_id, KEY, DAY) == cap


async def test_concurrent_plain_increments_are_monotonic() -> None:
    """Concurrent plain increments produce strictly monotonic, gapless totals."""
    requests = 15

    async with _TestSessionFactory() as session:
        user_id = await _seed_user(session)
        await session.commit()

    async def bump() -> int:
        async with _TestSessionFactory() as session:
            repo = UsageCounterRepository(session)
            total = await repo.increment(user_id, KEY, DAY, amount=1)
            await session.commit()
            return total

    results = await asyncio.gather(*(bump() for _ in range(requests)))
    assert sorted(results) == list(range(1, requests + 1))
