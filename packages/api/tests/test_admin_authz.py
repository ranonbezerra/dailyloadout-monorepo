"""Backoffice (Epic 21) Phase 1: admin authorization.

Admin rights are a grant row in ``admin_users`` — never a flag on the user row
and never a JWT claim — so they are checked against the DB on every request.
These tests cover the ``require_admin`` boundary (``GET /internal/v1/me``) and
the ``AdminRepository`` grant/revoke semantics.
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from dailyloadout.infrastructure.db.models import AdminUser, User
from dailyloadout.infrastructure.db.repositories.admin import AdminRepository
from tests.conftest import _TestSessionFactory


async def _register(client: AsyncClient, email: str) -> dict[str, Any]:
    payload = {
        "email": email,
        "password": "SecurePass1",  # pragma: allowlist secret
        "display_name": "BO User",
    }
    resp = await client.post("/v1/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _grant_admin(email: str) -> int:
    """Grant admin to the user with *email* and return their internal id."""
    async with _TestSessionFactory() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one()
        await AdminRepository(session).grant(user.id)
        await session.commit()
        return user.id


# =====================================================================
# require_admin boundary (GET /internal/v1/me)
# =====================================================================


class TestRequireAdmin:
    async def test_unauthenticated_is_401(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/internal/v1/me")
        assert resp.status_code == 401

    async def test_non_admin_user_is_403(self, async_client: AsyncClient) -> None:
        tokens = await _register(async_client, "plain@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        resp = await async_client.get("/internal/v1/me", headers=headers)
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Admin access required"

    async def test_admin_user_gets_identity(self, async_client: AsyncClient) -> None:
        tokens = await _register(async_client, "boss@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        await _grant_admin("boss@example.com")

        resp = await async_client.get("/internal/v1/me", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "boss@example.com"
        assert body["display_name"] == "BO User"
        assert "public_id" in body
        # The privilege flag must never bleed into the identity payload.
        assert "is_admin" not in body

    async def test_revoked_grant_is_enforced_immediately(self, async_client: AsyncClient) -> None:
        tokens = await _register(async_client, "temp@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        user_id = await _grant_admin("temp@example.com")

        # Granted → 200.
        assert (await async_client.get("/internal/v1/me", headers=headers)).status_code == 200

        # Revoke directly; the SAME token must now be rejected (no JWT claim to
        # rely on — admin-ness is re-checked against the DB every request).
        async with _TestSessionFactory() as session:
            removed = await AdminRepository(session).revoke(user_id)
            await session.commit()
            assert removed is True

        resp = await async_client.get("/internal/v1/me", headers=headers)
        assert resp.status_code == 403

    async def test_single_user_mode_blocks_backoffice(
        self, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The JWT-bypass single-user account must never reach the backoffice.
        from dailyloadout.deps import auth as auth_deps

        tokens = await _register(async_client, "solo@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        await _grant_admin("solo@example.com")
        monkeypatch.setattr(auth_deps.settings, "single_user_mode", True)
        monkeypatch.setattr(auth_deps.settings, "single_user_email", "solo@example.com")

        resp = await async_client.get("/internal/v1/me", headers=headers)
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Admin access not available"


# =====================================================================
# AdminRepository
# =====================================================================


class TestAdminRepository:
    async def _make_user(self, email: str) -> int:
        async with _TestSessionFactory() as session:
            user = User(email=email, password_hash="x", display_name="R")
            session.add(user)
            await session.flush()
            uid = user.id
            await session.commit()
            return uid

    async def test_is_admin_false_then_true(self) -> None:
        uid = await self._make_user("repo-a@example.com")
        async with _TestSessionFactory() as session:
            repo = AdminRepository(session)
            assert await repo.is_admin(uid) is False
            await repo.grant(uid)
            await session.commit()
            assert await repo.is_admin(uid) is True

    async def test_grant_is_idempotent(self) -> None:
        uid = await self._make_user("repo-b@example.com")
        async with _TestSessionFactory() as session:
            repo = AdminRepository(session)
            first = await repo.grant(uid)
            second = await repo.grant(uid)
            await session.commit()
            assert first.id == second.id
            # Exactly one grant row exists for the user.
            rows = (
                (await session.execute(select(AdminUser).where(AdminUser.user_id == uid)))
                .scalars()
                .all()
            )
            assert len(rows) == 1

    async def test_revoke_returns_false_when_absent(self) -> None:
        uid = await self._make_user("repo-c@example.com")
        async with _TestSessionFactory() as session:
            repo = AdminRepository(session)
            assert await repo.revoke(uid) is False
            await repo.grant(uid)
            await session.commit()
            assert await repo.revoke(uid) is True
            await session.commit()
            assert await repo.is_admin(uid) is False

    async def test_grant_records_granted_by(self) -> None:
        granter = await self._make_user("granter@example.com")
        grantee = await self._make_user("grantee@example.com")
        async with _TestSessionFactory() as session:
            await AdminRepository(session).grant(grantee, granted_by=granter)
            await session.commit()
            row = (
                await session.execute(select(AdminUser).where(AdminUser.user_id == grantee))
            ).scalar_one()
            assert row.granted_by == granter
