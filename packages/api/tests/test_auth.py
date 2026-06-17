"""Comprehensive tests for the auth endpoints (v1/auth/*)."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

# =====================================================================
# Registration
# =====================================================================


class TestRegister:
    """POST /v1/auth/register"""

    async def test_register_success(self, async_client: AsyncClient) -> None:
        payload = {
            "email": "newuser@example.com",
            "password": "securepassword",
            "display_name": "New User",
        }
        resp = await async_client.post("/v1/auth/register", json=payload)

        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_register_duplicate_email(self, async_client: AsyncClient) -> None:
        payload = {
            "email": "dupe@example.com",
            "password": "securepassword",
            "display_name": "First User",
        }
        resp1 = await async_client.post("/v1/auth/register", json=payload)
        assert resp1.status_code == 201

        resp2 = await async_client.post("/v1/auth/register", json=payload)
        assert resp2.status_code == 409

    async def test_register_invalid_email(self, async_client: AsyncClient) -> None:
        payload = {
            "email": "not-an-email",
            "password": "securepassword",
            "display_name": "Bad Email",
        }
        resp = await async_client.post("/v1/auth/register", json=payload)
        assert resp.status_code == 422

    async def test_register_short_password(self, async_client: AsyncClient) -> None:
        payload = {
            "email": "short@example.com",
            "password": "abc",
            "display_name": "Short Pass",
        }
        resp = await async_client.post("/v1/auth/register", json=payload)
        assert resp.status_code == 422


# =====================================================================
# Login
# =====================================================================


class TestLogin:
    """POST /v1/auth/login"""

    async def _register(self, client: AsyncClient) -> dict[str, Any]:
        payload = {
            "email": "login@example.com",
            "password": "securepassword",
            "display_name": "Login User",
        }
        resp = await client.post("/v1/auth/register", json=payload)
        assert resp.status_code == 201
        return resp.json()

    async def test_login_success(self, async_client: AsyncClient) -> None:
        await self._register(async_client)

        resp = await async_client.post(
            "/v1/auth/login",
            json={"email": "login@example.com", "password": "securepassword"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_login_wrong_password(self, async_client: AsyncClient) -> None:
        await self._register(async_client)

        resp = await async_client.post(
            "/v1/auth/login",
            json={"email": "login@example.com", "password": "wrongpassword"},
        )
        assert resp.status_code == 401

    async def test_login_nonexistent_user(self, async_client: AsyncClient) -> None:
        resp = await async_client.post(
            "/v1/auth/login",
            json={"email": "ghost@example.com", "password": "whatever123"},
        )
        assert resp.status_code == 401


# =====================================================================
# Refresh
# =====================================================================


class TestRefresh:
    """POST /v1/auth/refresh"""

    async def _register(self, client: AsyncClient) -> dict[str, Any]:
        payload = {
            "email": "refresh@example.com",
            "password": "securepassword",
            "display_name": "Refresh User",
        }
        resp = await client.post("/v1/auth/register", json=payload)
        assert resp.status_code == 201
        return resp.json()

    async def test_refresh_success(self, async_client: AsyncClient) -> None:
        tokens = await self._register(async_client)

        resp = await async_client.post(
            "/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_refresh_rotation(self, async_client: AsyncClient) -> None:
        """After a refresh, the old refresh token must be revoked and the
        new one must be valid."""
        tokens = await self._register(async_client)
        old_refresh = tokens["refresh_token"]

        # First refresh — should succeed and return new tokens.
        resp1 = await async_client.post(
            "/v1/auth/refresh",
            json={"refresh_token": old_refresh},
        )
        assert resp1.status_code == 200
        new_tokens = resp1.json()

        # The old refresh token is now revoked — using it again must fail.
        resp2 = await async_client.post(
            "/v1/auth/refresh",
            json={"refresh_token": old_refresh},
        )
        assert resp2.status_code == 401

        # The new refresh token should still work.
        resp3 = await async_client.post(
            "/v1/auth/refresh",
            json={"refresh_token": new_tokens["refresh_token"]},
        )
        assert resp3.status_code == 200

    async def test_refresh_invalid_token(self, async_client: AsyncClient) -> None:
        resp = await async_client.post(
            "/v1/auth/refresh",
            json={"refresh_token": "this-is-definitely-not-a-real-token"},
        )
        assert resp.status_code == 401


# =====================================================================
# Logout
# =====================================================================


class TestLogout:
    """POST /v1/auth/logout"""

    async def _register(self, client: AsyncClient) -> dict[str, Any]:
        payload = {
            "email": "logout@example.com",
            "password": "securepassword",
            "display_name": "Logout User",
        }
        resp = await client.post("/v1/auth/register", json=payload)
        assert resp.status_code == 201
        return resp.json()

    async def test_logout_success(self, async_client: AsyncClient) -> None:
        tokens = await self._register(async_client)

        resp = await async_client.post(
            "/v1/auth/logout",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Logged out"

    async def test_logout_token_revoked(self, async_client: AsyncClient) -> None:
        """After logout, attempting to refresh with the same token must fail."""
        tokens = await self._register(async_client)
        refresh = tokens["refresh_token"]

        # Logout
        resp_logout = await async_client.post(
            "/v1/auth/logout",
            json={"refresh_token": refresh},
        )
        assert resp_logout.status_code == 200

        # Refresh with the revoked token — must be rejected.
        resp_refresh = await async_client.post(
            "/v1/auth/refresh",
            json={"refresh_token": refresh},
        )
        assert resp_refresh.status_code == 401


# =====================================================================
# Me
# =====================================================================


class TestMe:
    """GET /v1/auth/me"""

    async def test_me_authenticated(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await async_client.get("/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200

        data = resp.json()
        assert data["email"] == "test@example.com"
        assert data["display_name"] == "Test Player"
        assert "public_id" in data

    async def test_me_no_token(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/v1/auth/me")
        assert resp.status_code == 401

    async def test_me_invalid_token(self, async_client: AsyncClient) -> None:
        headers = {"Authorization": "Bearer totally.bogus.token"}
        resp = await async_client.get("/v1/auth/me", headers=headers)
        assert resp.status_code == 401
