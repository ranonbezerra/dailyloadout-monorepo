"""Backoffice (Epic 21) Phase 4: dashboard aggregate endpoint.

`GET /internal/v1/dashboard` returns at-a-glance counts (users/banned/unverified/
admins, active missions, catalogue size, config overrides) plus the most recent
admin actions. Admin-gated like the rest of the backoffice.
"""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient
from sqlalchemy import select

from dailyloadout.infrastructure.db.models import Game, User
from dailyloadout.infrastructure.db.repositories.admin import AdminRepository
from tests.conftest import _TestSessionFactory


async def _register(client: AsyncClient, email: str) -> dict[str, Any]:
    payload = {
        "email": email,
        "password": "SecurePass1",  # pragma: allowlist secret
        "display_name": "Dash User",
    }
    resp = await client.post("/v1/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _admin_headers(
    client: AsyncClient, email: str = "dashadmin@example.com"
) -> dict[str, str]:
    tokens = await _register(client, email)
    async with _TestSessionFactory() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one()
        await AdminRepository(session).grant(user.id)
        await session.commit()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _make_user(email: str, *, banned: bool = False, verified: bool = True) -> None:
    async with _TestSessionFactory() as session:
        session.add(
            User(
                email=email,
                password_hash="x",  # pragma: allowlist secret
                display_name=email.split("@")[0],
                is_banned=banned,
                email_verified=verified,
            )
        )
        await session.commit()


class TestDashboard:
    async def test_requires_admin(self, async_client: AsyncClient) -> None:
        assert (await async_client.get("/internal/v1/dashboard")).status_code == 401
        tokens = await _register(async_client, "plain@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        assert (
            await async_client.get("/internal/v1/dashboard", headers=headers)
        ).status_code == 403

    async def test_summary_counts_and_recent_actions(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        await _make_user("banned@example.com", banned=True)
        await _make_user("unverified@example.com", verified=False)
        async with _TestSessionFactory() as session:
            session.add(
                Game(title="Catalogued", slug="catalogued", metadata_source="igdb", is_shared=True)
            )
            await session.commit()

        # Produce one audited action so recent_actions is non-empty.
        list_resp = await async_client.get("/internal/v1/users?q=banned@", headers=headers)
        target = list_resp.json()["items"][0]["public_id"]
        await async_client.post(f"/internal/v1/users/{target}/unban", headers=headers)

        resp = await async_client.get("/internal/v1/dashboard", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        # admin + banned + unverified + (the unbanned one is the banned user) → 3 users
        assert body["users_total"] == 3
        assert body["users_banned"] == 0  # we just unbanned the only banned user
        assert body["users_unverified"] == 1
        assert body["admins"] == 1
        assert body["catalogue_size"] == 1
        assert body["missions_active"] == 0
        assert body["config_overrides"] == 0
        assert body["recent_actions"]
        assert body["recent_actions"][0]["action"] == "user.unban"
