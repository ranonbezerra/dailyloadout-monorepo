"""Backoffice (Epic 21) Phase 5: games / catalogue admin.

Covers `/internal/v1/games` — list/search with owner counts + provenance
filters, detail, and the moderation actions (demote/promote/edit). Admin-gated
and audited like the rest of the backoffice.
"""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient
from sqlalchemy import func, select

from dailyloadout.infrastructure.db.models import (
    AdminAuditLog,
    Game,
    LibraryEntry,
    Platform,
    User,
)
from dailyloadout.infrastructure.db.repositories.admin import AdminRepository
from tests.conftest import _TestSessionFactory


async def _register(client: AsyncClient, email: str) -> dict[str, Any]:
    payload = {
        "email": email,
        "password": "SecurePass1",  # pragma: allowlist secret
        "display_name": "Cat Admin",
    }
    resp = await client.post("/v1/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _admin_headers(
    client: AsyncClient, email: str = "catadmin@example.com"
) -> dict[str, str]:
    tokens = await _register(client, email)
    async with _TestSessionFactory() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one()
        await AdminRepository(session).grant(user.id)
        await session.commit()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _make_game(
    *, slug: str, title: str, igdb_id: int | None = None, is_shared: bool = False, owners: int = 0
) -> str:
    """Create a game (+ optional owner library entries) and return its public_id."""
    async with _TestSessionFactory() as session:
        game = Game(
            slug=slug,
            title=title,
            metadata_source="igdb" if igdb_id else "manual",
            igdb_id=igdb_id,
            is_shared=is_shared,
        )
        session.add(game)
        await session.flush()
        pid = str(game.public_id)
        if owners:
            platform = Platform(slug=f"pc-{slug}", label="PC", family="pc")
            session.add(platform)
            await session.flush()
            for i in range(owners):
                user = User(
                    email=f"owner{i}-{slug}@example.com",
                    password_hash="x",  # pragma: allowlist secret
                    display_name=f"Owner {i}",
                )
                session.add(user)
                await session.flush()
                session.add(
                    LibraryEntry(user_id=user.id, game_id=game.id, platform_id=platform.id)
                )
        await session.commit()
        return pid


class TestGamesAuthz:
    async def test_list_requires_admin(self, async_client: AsyncClient) -> None:
        assert (await async_client.get("/internal/v1/games")).status_code == 401
        tokens = await _register(async_client, "plain@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        assert (await async_client.get("/internal/v1/games", headers=headers)).status_code == 403


class TestGamesList:
    async def test_lists_with_owner_counts_and_tallies(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        await _make_game(slug="halo", title="Halo", igdb_id=111, is_shared=True, owners=2)
        await _make_game(slug="indie", title="Indie Gem", is_shared=False)

        resp = await async_client.get("/internal/v1/games", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["catalogue_total"] == 2
        assert body["catalogue_igdb"] == 1
        assert body["catalogue_manual"] == 1
        by_slug = {g["slug"]: g for g in body["items"]}
        assert by_slug["halo"]["owner_count"] == 2
        assert by_slug["halo"]["source"] == "igdb"
        assert by_slug["indie"]["source"] == "manual"

    async def test_filters_by_source_and_shared(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        await _make_game(slug="halo", title="Halo", igdb_id=111, is_shared=True)
        await _make_game(slug="indie", title="Indie Gem", is_shared=False)

        manual = await async_client.get("/internal/v1/games?source=manual", headers=headers)
        assert [g["slug"] for g in manual.json()["items"]] == ["indie"]

        shared = await async_client.get("/internal/v1/games?shared=true", headers=headers)
        assert [g["slug"] for g in shared.json()["items"]] == ["halo"]

    async def test_search_matches_title(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        await _make_game(slug="halo", title="Halo Infinite", igdb_id=111)
        await _make_game(slug="indie", title="Indie Gem")
        resp = await async_client.get("/internal/v1/games?q=infinite", headers=headers)
        assert [g["slug"] for g in resp.json()["items"]] == ["halo"]


class TestGamesModeration:
    async def test_detail_and_404(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        pid = await _make_game(slug="halo", title="Halo", igdb_id=111, is_shared=True, owners=1)
        resp = await async_client.get(f"/internal/v1/games/{pid}", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["slug"] == "halo"
        assert body["owner_count"] == 1
        assert body["metadata_source"] == "igdb"

        missing = await async_client.get(
            "/internal/v1/games/00000000-0000-0000-0000-000000000000", headers=headers
        )
        assert missing.status_code == 404

    async def test_demote_sets_private_and_audits(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        pid = await _make_game(slug="spam", title="Spam Game", is_shared=True)
        resp = await async_client.post(f"/internal/v1/games/{pid}/demote", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["is_shared"] is False
        async with _TestSessionFactory() as session:
            row = (
                (await session.execute(select(AdminAuditLog).order_by(AdminAuditLog.id.desc())))
                .scalars()
                .first()
            )
            assert row is not None and row.action == "game.demote" and row.detail == "spam"

    async def test_promote_sets_shared_and_audits(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        pid = await _make_game(slug="gem", title="Hidden Gem", is_shared=False)
        resp = await async_client.post(f"/internal/v1/games/{pid}/promote", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["is_shared"] is True
        async with _TestSessionFactory() as session:
            count = (
                await session.execute(
                    select(func.count())
                    .select_from(AdminAuditLog)
                    .where(AdminAuditLog.action == "game.promote")
                )
            ).scalar_one()
            assert count == 1

    async def test_edit_updates_fields_and_audits(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        pid = await _make_game(slug="typo", title="Typo Title", is_shared=True)
        resp = await async_client.patch(
            f"/internal/v1/games/{pid}",
            headers=headers,
            json={"title": "Typo Title", "summary": "A fixed summary."},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "Typo Title"
        assert body["summary"] == "A fixed summary."
        async with _TestSessionFactory() as session:
            row = (
                (await session.execute(select(AdminAuditLog).order_by(AdminAuditLog.id.desc())))
                .scalars()
                .first()
            )
            assert row is not None and row.action == "game.edit"
            assert "typo" in (row.detail or "")
