"""Tests for the pick auto-ignore worker."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from httpx import AsyncClient


async def _create_library_entry(
    client: AsyncClient,
    headers: dict[str, str],
    seed_platforms: list[dict[str, Any]],
) -> dict[str, Any]:
    resp = await client.post(
        "/v1/captures/text",
        json={"raw_text": "I bought Hollow Knight"},
        headers=headers,
    )
    assert resp.status_code == 201
    capture = resp.json()
    candidate = capture["candidates"][0]
    platform_id = seed_platforms[0]["id"]
    resp = await client.post(
        f"/v1/captures/{capture['public_id']}/candidates/{candidate['public_id']}/confirm",
        json={"platform_id": platform_id, "status": "playing"},
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


async def _create_pick(
    client: AsyncClient,
    headers: dict[str, str],
) -> dict[str, Any]:
    resp = await client.post(
        "/v1/picks",
        json={"mood": "chill", "available_minutes": 60, "mental_energy": "medium"},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()[0]


class TestAutoIgnore:
    async def test_stale_pick_gets_ignored(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        await _create_library_entry(async_client, auth_headers, seed_platforms)
        await _create_pick(async_client, auth_headers)

        from slate.infrastructure.db.models import Pick
        from tests.conftest import _TestSessionFactory

        async with _TestSessionFactory() as session:
            p = await session.get(Pick, 1)
            assert p is not None
            p.created_at = datetime.now(UTC) - timedelta(hours=25)
            await session.commit()

        from slate.infrastructure.db.repositories.pick import PickRepository
        from slate.workers.pick_auto_ignore import auto_ignore_stale_picks

        async with _TestSessionFactory() as session:
            repo = PickRepository(session)
            ignored = await auto_ignore_stale_picks(repo, max_hours=24)
            await session.commit()

        assert ignored == 1

        resp = await async_client.get("/v1/picks", headers=auth_headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert items[0]["action"] == "ignored"

    async def test_fresh_pick_not_ignored(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        await _create_library_entry(async_client, auth_headers, seed_platforms)
        await _create_pick(async_client, auth_headers)

        from slate.infrastructure.db.repositories.pick import PickRepository
        from slate.workers.pick_auto_ignore import auto_ignore_stale_picks
        from tests.conftest import _TestSessionFactory

        async with _TestSessionFactory() as session:
            repo = PickRepository(session)
            ignored = await auto_ignore_stale_picks(repo, max_hours=24)
            await session.commit()

        assert ignored == 0

    async def test_no_stale_returns_zero(self) -> None:
        from slate.infrastructure.db.repositories.pick import PickRepository
        from slate.workers.pick_auto_ignore import auto_ignore_stale_picks
        from tests.conftest import _TestSessionFactory

        async with _TestSessionFactory() as session:
            repo = PickRepository(session)
            ignored = await auto_ignore_stale_picks(repo, max_hours=24)

        assert ignored == 0
