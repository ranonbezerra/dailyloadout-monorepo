"""Backoffice (Epic 21) Phase 6: picks read-only browse.

Covers `/internal/v1/picks` — cross-user list/search with per-action tallies
and detail. Read-only (picks decay via the auto-ignore worker), admin-gated.
"""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient
from sqlalchemy import select

from slate.infrastructure.db.models import (
    Game,
    LibraryEntry,
    Pick,
    Platform,
    User,
)
from slate.infrastructure.db.repositories.admin import AdminRepository
from tests.conftest import _TestSessionFactory


async def _register(client: AsyncClient, email: str) -> dict[str, Any]:
    payload = {
        "email": email,
        "password": "SecurePass1",  # pragma: allowlist secret
        "display_name": "Pick Admin",
    }
    resp = await client.post("/v1/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _admin_headers(
    client: AsyncClient, email: str = "pickadmin@example.com"
) -> dict[str, str]:
    tokens = await _register(client, email)
    async with _TestSessionFactory() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one()
        await AdminRepository(session).grant(user.id)
        await session.commit()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _make_pick(
    *,
    email: str,
    action: str | None = None,
    game_title: str = "Hollow Knight",
    reasoning: str | None = "A calm metroidvania for a focused hour.",
) -> str:
    """Create an owner + library entry + a pick; return its public_id."""
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
        pick = Pick(
            user_id=user.id,
            library_entry_id=entry.id,
            mood="chill",
            available_minutes=60,
            mental_energy="medium",
            context="after work",
            reasoning=reasoning,
            action=action,
        )
        session.add(pick)
        await session.flush()
        pid = str(pick.public_id)
        await session.commit()
        return pid


class TestPicksAuthz:
    async def test_list_requires_admin(self, async_client: AsyncClient) -> None:
        assert (await async_client.get("/internal/v1/picks")).status_code == 401
        tokens = await _register(async_client, "plain@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        resp = await async_client.get("/internal/v1/picks", headers=headers)
        assert resp.status_code == 403


class TestPicksList:
    async def test_lists_with_tallies_and_game(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        await _make_pick(email="a@example.com", action=None, game_title="Celeste")
        await _make_pick(email="b@example.com", action="ignored")

        resp = await async_client.get("/internal/v1/picks", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        tallies = {row["action"]: row["count"] for row in body["action_counts"]}
        assert tallies == {"pending": 1, "ignored": 1}
        by_email = {pick["user_email"]: pick for pick in body["items"]}
        assert by_email["a@example.com"]["action"] == "pending"
        assert by_email["a@example.com"]["game_title"] == "Celeste"
        assert by_email["b@example.com"]["action"] == "ignored"

    async def test_filters_by_action(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        await _make_pick(email="a@example.com", action=None)
        await _make_pick(email="b@example.com", action="ignored")
        resp = await async_client.get("/internal/v1/picks?action=pending", headers=headers)
        assert [pick["user_email"] for pick in resp.json()["items"]] == ["a@example.com"]

    async def test_search_matches_owner_email(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        await _make_pick(email="alice@example.com")
        await _make_pick(email="bob@example.com")
        resp = await async_client.get("/internal/v1/picks?q=alice", headers=headers)
        assert [pick["user_email"] for pick in resp.json()["items"]] == ["alice@example.com"]


class TestPicksDetail:
    async def test_detail_and_404(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        pid = await _make_pick(
            email="a@example.com", game_title="Hades", reasoning="Quick roguelite run."
        )
        resp = await async_client.get(f"/internal/v1/picks/{pid}", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["game_title"] == "Hades"
        assert body["platform_label"] == "PC"
        assert body["reasoning"] == "Quick roguelite run."
        assert body["context"] == "after work"
        assert body["led_to_play_session"] is False
        assert body["action"] == "pending"

        missing = await async_client.get(
            "/internal/v1/picks/00000000-0000-0000-0000-000000000000", headers=headers
        )
        assert missing.status_code == 404
