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
            "password": "SecurePass1",
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
            "password": "SecurePass1",
            "display_name": "First User",
        }
        resp1 = await async_client.post("/v1/auth/register", json=payload)
        assert resp1.status_code == 201

        resp2 = await async_client.post("/v1/auth/register", json=payload)
        assert resp2.status_code == 409

    async def test_register_invalid_email(self, async_client: AsyncClient) -> None:
        payload = {
            "email": "not-an-email",
            "password": "SecurePass1",
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
            "password": "SecurePass1",
            "display_name": "Login User",
        }
        resp = await client.post("/v1/auth/register", json=payload)
        assert resp.status_code == 201
        return resp.json()

    async def test_login_success(self, async_client: AsyncClient) -> None:
        await self._register(async_client)

        resp = await async_client.post(
            "/v1/auth/login",
            json={"email": "login@example.com", "password": "SecurePass1"},
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
            "password": "SecurePass1",
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
        """After a refresh, the old refresh token is revoked and the new one is valid.

        Note: replaying the *already-rotated* old token now triggers reuse
        detection (theft signal) which cuts off the whole family — covered in
        detail by test_auth_kill_switch. Here we only assert the happy path:
        the rotated-out token is dead, and the new token keeps working as long
        as the old one is not replayed.
        """
        tokens = await self._register(async_client)
        old_refresh = tokens["refresh_token"]

        # First refresh — should succeed and return new tokens.
        resp1 = await async_client.post(
            "/v1/auth/refresh",
            json={"refresh_token": old_refresh},
        )
        assert resp1.status_code == 200
        new_tokens = resp1.json()

        # The new refresh token works and can itself be rotated.
        resp2 = await async_client.post(
            "/v1/auth/refresh",
            json={"refresh_token": new_tokens["refresh_token"]},
        )
        assert resp2.status_code == 200

        # The original (rotated-out) token is dead — replaying it fails.
        resp3 = await async_client.post(
            "/v1/auth/refresh",
            json={"refresh_token": old_refresh},
        )
        assert resp3.status_code == 401

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
            "password": "SecurePass1",
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

    async def test_me_deleted_user(self, async_client: AsyncClient) -> None:
        """A valid JWT for a user that no longer exists returns 401."""
        payload = {
            "email": "deleted@example.com",
            "password": "SecurePass1",
            "display_name": "Ghost",
        }
        resp = await async_client.post("/v1/auth/register", json=payload)
        assert resp.status_code == 201
        token = resp.json()["access_token"]

        # Delete the user directly from the DB.
        from dailyloadout.infrastructure.db.models import User
        from tests.conftest import _TestSessionFactory

        async with _TestSessionFactory() as session:
            from sqlalchemy import delete

            await session.execute(delete(User).where(User.email == "deleted@example.com"))
            await session.commit()

        headers = {"Authorization": f"Bearer {token}"}
        resp = await async_client.get("/v1/auth/me", headers=headers)
        assert resp.status_code == 401


_COOKIE_HEADER = {"X-Auth-Mode": "cookie"}
_COOKIE_NAME = "dl_refresh_token"


class TestCookieMode:
    """Web cookie-mode contract (X-Auth-Mode: cookie)."""

    async def test_register_sets_httponly_cookie_and_empty_body(
        self, async_client: AsyncClient
    ) -> None:
        resp = await async_client.post(
            "/v1/auth/register",
            json={
                "email": "cookie-reg@example.com",
                "password": "SecurePass1",
                "display_name": "Cookie Reg",
            },
            headers=_COOKIE_HEADER,
        )
        assert resp.status_code == 201
        # Body never exposes the refresh token in cookie mode.
        assert resp.json()["refresh_token"] == ""
        assert resp.json()["access_token"]
        # An httpOnly refresh cookie was set.
        assert _COOKIE_NAME in resp.cookies
        set_cookie = resp.headers.get("set-cookie", "")
        assert "httponly" in set_cookie.lower()

    async def test_login_sets_httponly_cookie_and_empty_body(
        self, async_client: AsyncClient
    ) -> None:
        await async_client.post(
            "/v1/auth/register",
            json={
                "email": "cookie-login@example.com",
                "password": "SecurePass1",
                "display_name": "Cookie Login",
            },
            headers=_COOKIE_HEADER,
        )
        resp = await async_client.post(
            "/v1/auth/login",
            json={"email": "cookie-login@example.com", "password": "SecurePass1"},
            headers=_COOKIE_HEADER,
        )
        assert resp.status_code == 200
        assert resp.json()["refresh_token"] == ""
        assert resp.json()["access_token"]
        assert _COOKIE_NAME in resp.cookies

    async def test_refresh_from_cookie_only_rotates_cookie(
        self, async_client: AsyncClient
    ) -> None:
        # The async_client persists cookies across requests like a browser.
        reg = await async_client.post(
            "/v1/auth/register",
            json={
                "email": "cookie-refresh@example.com",
                "password": "SecurePass1",
                "display_name": "Cookie Refresh",
            },
            headers=_COOKIE_HEADER,
        )
        old_cookie = reg.cookies[_COOKIE_NAME]

        # POST with no body, just the header — the cookie carries the token.
        resp = await async_client.post("/v1/auth/refresh", headers=_COOKIE_HEADER)
        assert resp.status_code == 200
        assert resp.json()["refresh_token"] == ""
        assert resp.json()["access_token"]
        # The cookie was rotated to a new value.
        assert _COOKIE_NAME in resp.cookies
        assert resp.cookies[_COOKIE_NAME] != old_cookie

    async def test_refresh_without_cookie_or_body_returns_401(
        self, async_client: AsyncClient
    ) -> None:
        resp = await async_client.post("/v1/auth/refresh", headers=_COOKIE_HEADER)
        assert resp.status_code == 401

    async def test_logout_clears_cookie_and_revokes(self, async_client: AsyncClient) -> None:
        await async_client.post(
            "/v1/auth/register",
            json={
                "email": "cookie-logout@example.com",
                "password": "SecurePass1",
                "display_name": "Cookie Logout",
            },
            headers=_COOKIE_HEADER,
        )
        resp = await async_client.post("/v1/auth/logout", headers=_COOKIE_HEADER)
        assert resp.status_code == 200
        # The Set-Cookie header clears the cookie (max-age=0 / expires in past).
        set_cookie = resp.headers.get("set-cookie", "")
        assert _COOKIE_NAME in set_cookie

        # After logout the cookie is gone, so a fresh refresh has no token → 401.
        async_client.cookies.delete(_COOKIE_NAME)
        resp_refresh = await async_client.post("/v1/auth/refresh", headers=_COOKIE_HEADER)
        assert resp_refresh.status_code == 401

    async def test_body_mode_still_returns_both_tokens(self, async_client: AsyncClient) -> None:
        """Regression: without the header the app contract is unchanged."""
        resp = await async_client.post(
            "/v1/auth/register",
            json={
                "email": "body-mode@example.com",
                "password": "SecurePass1",
                "display_name": "Body Mode",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["access_token"]
        assert data["refresh_token"]  # non-empty
        # No refresh cookie is set in body mode.
        assert _COOKIE_NAME not in resp.cookies

        # Body-mode refresh reads the token from the JSON body as before.
        resp_refresh = await async_client.post(
            "/v1/auth/refresh",
            json={"refresh_token": data["refresh_token"]},
        )
        assert resp_refresh.status_code == 200
        assert resp_refresh.json()["refresh_token"]


class TestRefreshDeletedUser:
    """Refresh token for a deleted user returns 401."""

    async def test_refresh_after_user_deleted(self, async_client: AsyncClient) -> None:
        payload = {
            "email": "gone@example.com",
            "password": "SecurePass1",
            "display_name": "Gone User",
        }
        resp = await async_client.post("/v1/auth/register", json=payload)
        assert resp.status_code == 201
        refresh_token = resp.json()["refresh_token"]

        from dailyloadout.infrastructure.db.models import User
        from tests.conftest import _TestSessionFactory

        async with _TestSessionFactory() as session:
            from sqlalchemy import delete

            await session.execute(delete(User).where(User.email == "gone@example.com"))
            await session.commit()

        resp = await async_client.post(
            "/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 401
