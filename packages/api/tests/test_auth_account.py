"""Account-lifecycle endpoints: data export + self-service erasure (GDPR/LGPD)."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select

from slate.core.auth.email_change import create_email_change_token
from slate.core.auth.security import create_access_token
from slate.infrastructure.db.models import User
from tests.conftest import _TestSessionFactory

_EMAIL = "test@example.com"
_PASSWORD = "StrongPass123"  # pragma: allowlist secret


class TestDataExport:
    async def test_export_returns_the_users_data(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await async_client.get("/v1/auth/me/export", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        # The portable document has the profile + every personal-data collection.
        assert body["profile"]["email"] == _EMAIL
        assert set(body) >= {
            "exported_at",
            "profile",
            "library",
            "play_sessions",
            "captures",
            "picks",
        }
        assert isinstance(body["library"], list)

    async def test_export_requires_auth(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/v1/auth/me/export")
        assert resp.status_code == 401


class TestAccountDeletion:
    async def test_wrong_password_is_rejected(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await async_client.post(
            "/v1/auth/delete-account",
            headers=auth_headers,
            json={"password": "WrongPass123"},  # pragma: allowlist secret
        )
        assert resp.status_code == 403

    async def test_delete_erases_the_account(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await async_client.post(
            "/v1/auth/delete-account",
            headers=auth_headers,
            json={"password": _PASSWORD},
        )
        assert resp.status_code == 200

        # The row is gone: the old token no longer resolves, and login fails.
        me = await async_client.get("/v1/auth/me", headers=auth_headers)
        assert me.status_code == 401
        login = await async_client.post(
            "/v1/auth/login", json={"email": _EMAIL, "password": _PASSWORD}
        )
        assert login.status_code == 401
        async with _TestSessionFactory() as session:
            found = (
                await session.execute(select(User).where(User.email == _EMAIL))
            ).scalar_one_or_none()
        assert found is None

    async def test_oauth_only_account_deletes_without_password(
        self, async_client: AsyncClient
    ) -> None:
        # An OAuth-only user has no password to confirm; the authenticated session
        # is the gate. Seed one directly and mint its access token.
        async with _TestSessionFactory() as session:
            user = User(email="oauthonly@example.com", password_hash=None, display_name="OA")
            session.add(user)
            await session.commit()
            token = create_access_token(str(user.public_id), user.token_version)

        resp = await async_client.post(
            "/v1/auth/delete-account",
            headers={"Authorization": f"Bearer {token}"},
            json={"password": ""},
        )
        assert resp.status_code == 200

    async def test_delete_requires_auth(self, async_client: AsyncClient) -> None:
        resp = await async_client.post("/v1/auth/delete-account", json={"password": _PASSWORD})
        assert resp.status_code == 401


class TestEmailChange:
    async def test_request_change_succeeds(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await async_client.post(
            "/v1/auth/change-email",
            headers=auth_headers,
            json={"new_email": "brand-new@example.com", "password": _PASSWORD},
        )
        assert resp.status_code == 200
        # The email is NOT changed yet — only confirmed via the link.
        login = await async_client.post(
            "/v1/auth/login", json={"email": _EMAIL, "password": _PASSWORD}
        )
        assert login.status_code == 200

    async def test_request_change_wrong_password(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await async_client.post(
            "/v1/auth/change-email",
            headers=auth_headers,
            json={
                "new_email": "x@example.com",
                "password": "WrongPass123",
            },  # pragma: allowlist secret
        )
        assert resp.status_code == 403

    async def test_request_change_to_same_email(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await async_client.post(
            "/v1/auth/change-email",
            headers=auth_headers,
            json={"new_email": _EMAIL, "password": _PASSWORD},
        )
        assert resp.status_code == 400

    async def test_request_change_to_taken_email(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        await async_client.post(
            "/v1/auth/register",
            json={"email": "taken@example.com", "password": _PASSWORD, "display_name": "T"},
        )
        resp = await async_client.post(
            "/v1/auth/change-email",
            headers=auth_headers,
            json={"new_email": "taken@example.com", "password": _PASSWORD},
        )
        assert resp.status_code == 400

    async def test_confirm_applies_the_new_email(
        self, async_client: AsyncClient, register_user: dict[str, str]
    ) -> None:
        async with _TestSessionFactory() as session:
            user = (await session.execute(select(User).where(User.email == _EMAIL))).scalar_one()
            token = create_email_change_token(str(user.public_id), "confirmed@example.com")

        resp = await async_client.post("/v1/auth/confirm-email-change", json={"token": token})
        assert resp.status_code == 200
        # Login now works with the new address, not the old.
        new = await async_client.post(
            "/v1/auth/login", json={"email": "confirmed@example.com", "password": _PASSWORD}
        )
        assert new.status_code == 200
        old = await async_client.post(
            "/v1/auth/login", json={"email": _EMAIL, "password": _PASSWORD}
        )
        assert old.status_code == 401

    async def test_confirm_rejects_a_bad_token(self, async_client: AsyncClient) -> None:
        resp = await async_client.post(
            "/v1/auth/confirm-email-change", json={"token": "not-a-jwt"}
        )
        assert resp.status_code == 400
