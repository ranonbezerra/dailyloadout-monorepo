"""Backoffice (Epic 21) Phase 2: user management + audit log.

Covers the ``/internal/v1/users`` surface (list/search/filter, detail,
ban/unban/verify) and the ``/internal/v1/audit`` log. Every route is gated by
``require_admin``; every mutation must write an audit row and (for ban) kill the
target's sessions. Admins cannot be banned.
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from dailyloadout.infrastructure.db.models import AdminAuditLog, User
from dailyloadout.infrastructure.db.repositories.admin import AdminRepository
from tests.conftest import _TestSessionFactory


async def _register(
    client: AsyncClient, email: str, display_name: str = "BO User"
) -> dict[str, Any]:
    payload = {
        "email": email,
        "password": "SecurePass1",  # pragma: allowlist secret
        "display_name": display_name,
    }
    resp = await client.post("/v1/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _grant_admin(email: str) -> int:
    async with _TestSessionFactory() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one()
        await AdminRepository(session).grant(user.id)
        await session.commit()
        return user.id


async def _admin_headers(client: AsyncClient, email: str = "boss@example.com") -> dict[str, str]:
    tokens = await _register(client, email, display_name="Boss")
    await _grant_admin(email)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _public_id_of(email: str) -> str:
    async with _TestSessionFactory() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one()
        return str(user.public_id)


async def _audit_count() -> int:
    async with _TestSessionFactory() as session:
        return (
            await session.execute(select(func.count()).select_from(AdminAuditLog))
        ).scalar_one()


async def _make_user(email: str, *, email_verified: bool = True, banned: bool = False) -> str:
    """Create a user directly and return its public_id (string)."""
    async with _TestSessionFactory() as session:
        user = User(
            email=email,
            password_hash="x",  # pragma: allowlist secret
            display_name=email.split("@")[0],
            email_verified=email_verified,
            is_banned=banned,
        )
        session.add(user)
        await session.flush()
        pid = str(user.public_id)
        await session.commit()
        return pid


# =====================================================================
# Authorization boundary (shared by every route)
# =====================================================================

_ROUTES = [
    ("get", "/internal/v1/users"),
    ("get", "/internal/v1/users/00000000-0000-0000-0000-000000000000"),
    ("post", "/internal/v1/users/00000000-0000-0000-0000-000000000000/ban"),
    ("post", "/internal/v1/users/00000000-0000-0000-0000-000000000000/unban"),
    ("post", "/internal/v1/users/00000000-0000-0000-0000-000000000000/verify"),
    ("get", "/internal/v1/audit"),
]


class TestAuthz:
    @pytest.mark.parametrize(("method", "path"), _ROUTES)
    async def test_unauthenticated_is_401(
        self, async_client: AsyncClient, method: str, path: str
    ) -> None:
        resp = await async_client.request(method, path)
        assert resp.status_code == 401

    @pytest.mark.parametrize(("method", "path"), _ROUTES)
    async def test_non_admin_is_403(
        self, async_client: AsyncClient, method: str, path: str
    ) -> None:
        tokens = await _register(async_client, "plain@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        resp = await async_client.request(method, path, headers=headers)
        assert resp.status_code == 403


# =====================================================================
# List / search
# =====================================================================


class TestListUsers:
    async def test_lists_with_total_and_pagination(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        for i in range(3):
            await _make_user(f"user{i}@example.com")

        resp = await async_client.get("/internal/v1/users?limit=2", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        # 3 created + the admin = 4 total; page capped at 2.
        assert body["total"] == 4
        assert len(body["items"]) == 2
        assert body["limit"] == 2 and body["offset"] == 0
        # Privilege must never leak into the summary payload.
        assert "is_admin" not in body["items"][0]

    async def test_search_matches_email(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        await _make_user("needle@example.com")
        await _make_user("haystack@example.com")

        resp = await async_client.get("/internal/v1/users?q=needle", headers=headers)
        assert resp.status_code == 200
        emails = [u["email"] for u in resp.json()["items"]]
        assert emails == ["needle@example.com"]

    async def test_filter_banned_and_verified(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        await _make_user("banned@example.com", banned=True)
        await _make_user("unverified@example.com", email_verified=False)

        banned = await async_client.get("/internal/v1/users?banned=true", headers=headers)
        assert [u["email"] for u in banned.json()["items"]] == ["banned@example.com"]

        unverified = await async_client.get("/internal/v1/users?verified=false", headers=headers)
        assert [u["email"] for u in unverified.json()["items"]] == ["unverified@example.com"]


# =====================================================================
# Detail
# =====================================================================


class TestUserDetail:
    async def test_detail_includes_admin_fields(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        pid = await _make_user("detail@example.com")

        resp = await async_client.get(f"/internal/v1/users/{pid}", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "detail@example.com"
        assert body["is_admin"] is False
        assert body["has_password"] is True
        assert body["active_sessions"] == 0
        assert "locale" in body and "timezone" in body

    async def test_unknown_user_is_404(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        resp = await async_client.get(
            "/internal/v1/users/00000000-0000-0000-0000-000000000000", headers=headers
        )
        assert resp.status_code == 404


# =====================================================================
# Ban / unban / verify (audited)
# =====================================================================


class TestBan:
    async def test_ban_cuts_off_access_and_audits(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        # A real, logged-in victim so we can prove their session dies.
        victim = await _register(async_client, "victim@example.com")
        victim_headers = {"Authorization": f"Bearer {victim['access_token']}"}
        pid = await _public_id_of("victim@example.com")
        before = await _audit_count()

        # The victim can reach an authed route before the ban.
        assert (await async_client.get("/v1/auth/me", headers=victim_headers)).status_code == 200

        resp = await async_client.post(
            f"/internal/v1/users/{pid}/ban",
            headers=headers,
            json={"reason": "spamming"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["is_banned"] is True
        assert body["active_sessions"] == 0

        # The victim's previously-valid token no longer works.
        assert (await async_client.get("/v1/auth/me", headers=victim_headers)).status_code in (
            401,
            403,
        )
        # Exactly one audit row was appended, carrying the reason.
        async with _TestSessionFactory() as session:
            row = (
                (await session.execute(select(AdminAuditLog).order_by(AdminAuditLog.id.desc())))
                .scalars()
                .first()
            )
            assert row is not None
            assert row.action == "user.ban"
            assert row.detail == "spamming"
        assert await _audit_count() == before + 1

    async def test_cannot_ban_an_admin(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client, "boss@example.com")
        # A second admin — banning them must be refused.
        await _register(async_client, "peer@example.com")
        peer_id = await _grant_admin("peer@example.com")
        async with _TestSessionFactory() as session:
            peer = await session.get(User, peer_id)
            assert peer is not None
            peer_pid = str(peer.public_id)

        resp = await async_client.post(f"/internal/v1/users/{peer_pid}/ban", headers=headers)
        assert resp.status_code == 403
        assert "admin" in resp.json()["detail"].lower()

    async def test_ban_unknown_user_is_404(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        resp = await async_client.post(
            "/internal/v1/users/00000000-0000-0000-0000-000000000000/ban", headers=headers
        )
        assert resp.status_code == 404


class TestUnban:
    async def test_unban_clears_flag_and_audits(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        pid = await _make_user("rehab@example.com", banned=True)

        resp = await async_client.post(f"/internal/v1/users/{pid}/unban", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["is_banned"] is False

        async with _TestSessionFactory() as session:
            row = (
                (await session.execute(select(AdminAuditLog).order_by(AdminAuditLog.id.desc())))
                .scalars()
                .first()
            )
            assert row is not None and row.action == "user.unban"

    async def test_unban_unknown_user_is_404(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        resp = await async_client.post(
            "/internal/v1/users/00000000-0000-0000-0000-000000000000/unban", headers=headers
        )
        assert resp.status_code == 404


class TestVerify:
    async def test_verify_marks_verified_and_audits(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        pid = await _make_user("toverify@example.com", email_verified=False)

        resp = await async_client.post(f"/internal/v1/users/{pid}/verify", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["email_verified"] is True

        # Idempotent: verifying again still 200s and audits again.
        resp2 = await async_client.post(f"/internal/v1/users/{pid}/verify", headers=headers)
        assert resp2.status_code == 200

        async with _TestSessionFactory() as session:
            count = (
                await session.execute(
                    select(func.count())
                    .select_from(AdminAuditLog)
                    .where(AdminAuditLog.action == "user.verify")
                )
            ).scalar_one()
            assert count == 2

    async def test_verify_unknown_user_is_404(self, async_client: AsyncClient) -> None:
        headers = await _admin_headers(async_client)
        resp = await async_client.post(
            "/internal/v1/users/00000000-0000-0000-0000-000000000000/verify", headers=headers
        )
        assert resp.status_code == 404


# =====================================================================
# Audit log read
# =====================================================================


class TestAuditLog:
    async def test_lists_actions_newest_first_with_identities(
        self, async_client: AsyncClient
    ) -> None:
        headers = await _admin_headers(async_client, "auditor@example.com")
        pid = await _make_user("subject@example.com", banned=True)
        await async_client.post(f"/internal/v1/users/{pid}/unban", headers=headers)
        await async_client.post(f"/internal/v1/users/{pid}/verify", headers=headers)

        resp = await async_client.get("/internal/v1/audit", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        # Newest first: verify before unban.
        assert body["items"][0]["action"] == "user.verify"
        assert body["items"][1]["action"] == "user.unban"
        entry = body["items"][0]
        assert entry["admin_email"] == "auditor@example.com"
        assert entry["target_email"] == "subject@example.com"
