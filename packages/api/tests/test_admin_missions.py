"""Backoffice (Epic 21) Phase 6: missions moderation.

Covers `/internal/v1/missions` — cross-user list/search with per-status tallies,
detail, and force-clamp (ends a stuck active mission, the panel counterpart to
the periodic auto-clamp). Admin-gated and audited like the rest of the
backoffice.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from httpx import AsyncClient
from sqlalchemy import func, select

from dailyloadout.infrastructure.db.models import (
    AdminAuditLog,
    Game,
    LibraryEntry,
    Mission,
    Platform,
    User,
)
from dailyloadout.infrastructure.db.repositories.admin import AdminRepository
from tests.conftest import _TestSessionFactory


async def _register(client: AsyncClient, email: str) -> dict[str, Any]:
    payload = {
        "email": email,
        "password": "SecurePass1",  # pragma: allowlist secret
        "display_name": "Mission Admin",
    }
    resp = await client.post("/v1/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _admin_headers(
    client: AsyncClient, email: str = "missionadmin@example.com"
) -> dict[str, str]:
    tokens = await _register(client, email)
    async with _TestSessionFactory() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one()
        await AdminRepository(session).grant(user.id)
        await session.commit()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _make_mission(
    *,
    email: str,
    ended: bool = False,
    game_title: str = "Hollow Knight",
) -> str:
    """Create an owner + library entry + a mission; return its public_id."""
    async with _TestSessionFactory() as session:
        user = User(
            email=email,
            password_hash="x",  # pragma: allowlist secret
            display_name="Owner",
        )
        session.add(user)
        await session.flush()
        game = Game(slug=f"game-{user.id}", title=game_title, metadata_source="user")
        platform = Platform(slug=f"pc-{user.id}", label="PC", family="pc")
        session.add_all([game, platform])
        await session.flush()
        entry = LibraryEntry(
            user_id=user.id, game_id=game.id, platform_id=platform.id, status="playing"
        )
        session.add(entry)
        await session.flush()
        now = datetime.now(UTC)
        mission = Mission(
            user_id=user.id,
            library_entry_id=entry.id,
            mission_type="regular",
            briefing_text="Go beat the boss",
            started_at=now - timedelta(hours=2),
            ended_at=now if ended else None,
            ended_via="debrief_completed" if ended else None,
            debrief_text="cleared it" if ended else None,
        )
        session.add(mission)
        await session.flush()
        pid = str(mission.public_id)
        await session.commit()
        return pid


class TestMissionsAuthz:
    async def test_list_requires_admin(self, async_client: AsyncClient) -> None:
        assert (await async_client.get("/internal/v1/missions")).status_code == 401
        tokens = await _register(async_client, "plain@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        resp = await async_client.get("/internal/v1/missions", headers=headers)
        assert resp.status_code == 403


class TestMissionsList:
    async def test_lists_with_tallies_and_game(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        await _make_mission(email="a@example.com", ended=False, game_title="Celeste")
        await _make_mission(email="b@example.com", ended=True)

        resp = await async_client.get("/internal/v1/missions", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        tallies = {row["status"]: row["count"] for row in body["status_counts"]}
        assert tallies == {"active": 1, "ended": 1}
        by_email = {m["user_email"]: m for m in body["items"]}
        assert by_email["a@example.com"]["status"] == "active"
        assert by_email["a@example.com"]["game_title"] == "Celeste"
        assert by_email["b@example.com"]["status"] == "ended"

    async def test_filters_by_status(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        await _make_mission(email="a@example.com", ended=False)
        await _make_mission(email="b@example.com", ended=True)
        resp = await async_client.get("/internal/v1/missions?status=active", headers=headers)
        assert [m["user_email"] for m in resp.json()["items"]] == ["a@example.com"]

    async def test_search_matches_owner_email(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        await _make_mission(email="alice@example.com")
        await _make_mission(email="bob@example.com")
        resp = await async_client.get("/internal/v1/missions?q=alice", headers=headers)
        assert [m["user_email"] for m in resp.json()["items"]] == ["alice@example.com"]


class TestMissionsModeration:
    async def test_detail_and_404(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        pid = await _make_mission(email="a@example.com", game_title="Hades")
        resp = await async_client.get(f"/internal/v1/missions/{pid}", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["game_title"] == "Hades"
        assert body["platform_label"] == "PC"
        assert body["briefing_text"] == "Go beat the boss"
        assert body["status"] == "active"

        missing = await async_client.get(
            "/internal/v1/missions/00000000-0000-0000-0000-000000000000", headers=headers
        )
        assert missing.status_code == 404

    async def test_clamp_ends_active_and_audits(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        pid = await _make_mission(email="a@example.com", ended=False)
        resp = await async_client.post(f"/internal/v1/missions/{pid}/clamp", headers=headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "ended"
        assert body["ended_via"] == "admin_clamp"
        assert body["ended_at"] is not None
        async with _TestSessionFactory() as session:
            row = (
                (await session.execute(select(AdminAuditLog).order_by(AdminAuditLog.id.desc())))
                .scalars()
                .first()
            )
            assert row is not None and row.action == "mission.clamp"

    async def test_clamp_rejects_already_ended(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        pid = await _make_mission(email="a@example.com", ended=True)
        resp = await async_client.post(f"/internal/v1/missions/{pid}/clamp", headers=headers)
        assert resp.status_code == 409

    async def test_clamp_404_for_unknown(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        resp = await async_client.post(
            "/internal/v1/missions/00000000-0000-0000-0000-000000000000/clamp", headers=headers
        )
        assert resp.status_code == 404
        # No audit row written for a no-op.
        async with _TestSessionFactory() as session:
            count = (
                await session.execute(
                    select(func.count())
                    .select_from(AdminAuditLog)
                    .where(AdminAuditLog.action == "mission.clamp")
                )
            ).scalar_one()
            assert count == 0
