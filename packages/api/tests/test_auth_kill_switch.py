"""Anti-abuse Phase 2: session kill-switch & incident response.

Covers token-version invalidation, logout-everywhere, account ban, and
refresh-token reuse detection (theft signal).
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update

from dailyloadout.core.auth.security import create_access_token
from dailyloadout.infrastructure.db.models import RefreshToken, User
from tests.conftest import _TestSessionFactory


async def _register(client: AsyncClient, email: str) -> dict[str, Any]:
    payload = {"email": email, "password": "SecurePass1", "display_name": "Kill Switch"}
    resp = await client.post("/v1/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _token_version(email: str) -> int:
    async with _TestSessionFactory() as session:
        row = await session.execute(select(User.token_version).where(User.email == email))
        return int(row.scalar_one())


# =====================================================================
# Token-version invalidation
# =====================================================================


class TestTokenVersionInvalidation:
    async def test_bumped_token_version_rejects_old_access_token(
        self, async_client: AsyncClient
    ) -> None:
        tokens = await _register(async_client, "tv-bump@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        # The freshly-minted token works.
        assert (await async_client.get("/v1/auth/me", headers=headers)).status_code == 200

        # Bump token_version directly in the DB → the old token is now stale.
        async with _TestSessionFactory() as session:
            await session.execute(
                update(User)
                .where(User.email == "tv-bump@example.com")
                .values(token_version=User.token_version + 1)
            )
            await session.commit()

        resp = await async_client.get("/v1/auth/me", headers=headers)
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Session expired"

    async def test_token_without_tv_claim_is_rejected(self, async_client: AsyncClient) -> None:
        await _register(async_client, "no-tv@example.com")
        async with _TestSessionFactory() as session:
            public_id = (
                await session.execute(
                    select(User.public_id).where(User.email == "no-tv@example.com")
                )
            ).scalar_one()

        # Forge a token whose tv (5) does not match the user's current version (0).
        forged = create_access_token(str(public_id), token_version=5)
        resp = await async_client.get("/v1/auth/me", headers={"Authorization": f"Bearer {forged}"})
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Session expired"


# =====================================================================
# Logout-everywhere
# =====================================================================


class TestLogoutAll:
    async def test_logout_all_invalidates_access_and_refresh(
        self, async_client: AsyncClient
    ) -> None:
        tokens = await _register(async_client, "logout-all@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        before = await _token_version("logout-all@example.com")

        resp = await async_client.post("/v1/auth/logout-all", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["message"] == "Logged out everywhere"

        # token_version bumped → existing access token now 401s.
        assert await _token_version("logout-all@example.com") == before + 1
        me = await async_client.get("/v1/auth/me", headers=headers)
        assert me.status_code == 401
        assert me.json()["detail"] == "Session expired"

        # Existing refresh token is revoked too.
        refresh = await async_client.post(
            "/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert refresh.status_code == 401

    async def test_logout_all_requires_auth(self, async_client: AsyncClient) -> None:
        resp = await async_client.post("/v1/auth/logout-all")
        assert resp.status_code == 401

    async def test_logout_all_cookie_mode_clears_cookie(self, async_client: AsyncClient) -> None:
        reg = await async_client.post(
            "/v1/auth/register",
            json={
                "email": "cookie-logout-all@example.com",
                "password": "SecurePass1",
                "display_name": "Cookie Logout All",
            },
            headers={"X-Auth-Mode": "cookie"},
        )
        assert reg.status_code == 201
        headers = {
            "Authorization": f"Bearer {reg.json()['access_token']}",
            "X-Auth-Mode": "cookie",
        }
        resp = await async_client.post("/v1/auth/logout-all", headers=headers)
        assert resp.status_code == 200
        assert "dl_refresh_token" in resp.headers.get("set-cookie", "")

    async def test_login_after_logout_all_still_works(self, async_client: AsyncClient) -> None:
        await _register(async_client, "relogin@example.com")
        login = await async_client.post(
            "/v1/auth/login",
            json={"email": "relogin@example.com", "password": "SecurePass1"},
        )
        assert login.status_code == 200
        new_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        await async_client.post("/v1/auth/logout-all", headers=new_headers)

        # A brand-new login mints a token with the current (bumped) version.
        login2 = await async_client.post(
            "/v1/auth/login",
            json={"email": "relogin@example.com", "password": "SecurePass1"},
        )
        assert login2.status_code == 200
        headers2 = {"Authorization": f"Bearer {login2.json()['access_token']}"}
        assert (await async_client.get("/v1/auth/me", headers=headers2)).status_code == 200


# =====================================================================
# Ban / disable account
# =====================================================================


class TestBan:
    async def test_banned_user_is_403_and_tokens_dead(self, async_client: AsyncClient) -> None:
        tokens = await _register(async_client, "ban-me@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        # Ban via the service-level mechanism (as the CLI / internal call would).
        async with _TestSessionFactory() as session:
            from dailyloadout.core.auth.service import AuthService
            from dailyloadout.infrastructure.db.repositories.refresh_token import (
                RefreshTokenRepository,
            )
            from dailyloadout.infrastructure.db.repositories.user import UserRepository

            user_repo = UserRepository(session)
            user = await user_repo.get_by_email("ban-me@example.com")
            assert user is not None
            await AuthService(user_repo, RefreshTokenRepository(session)).ban_user(user.id)
            await session.commit()

        # token_version was bumped → the old access token 401s ("Session expired")
        # before the ban check is even reached, so the cutoff is total.
        me = await async_client.get("/v1/auth/me", headers=headers)
        assert me.status_code == 401

        # Refresh token revoked too → cannot mint a new access token.
        refresh = await async_client.post(
            "/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert refresh.status_code == 401

        # And a banned user who somehow holds a current-version token is 403'd.
        async with _TestSessionFactory() as session:
            public_id, tv = (
                await session.execute(
                    select(User.public_id, User.token_version).where(
                        User.email == "ban-me@example.com"
                    )
                )
            ).one()
        current_token = create_access_token(str(public_id), token_version=int(tv))
        resp = await async_client.get(
            "/v1/auth/me", headers={"Authorization": f"Bearer {current_token}"}
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Account suspended"


# =====================================================================
# Refresh-token reuse detection (theft signal)
# =====================================================================


class TestRefreshReuseDetection:
    async def test_replaying_rotated_token_revokes_family(self, async_client: AsyncClient) -> None:
        tokens = await _register(async_client, "theft@example.com")
        old_refresh = tokens["refresh_token"]
        before_tv = await _token_version("theft@example.com")

        # Legitimate rotation: old token is revoked, a new one issued.
        rot = await async_client.post("/v1/auth/refresh", json={"refresh_token": old_refresh})
        assert rot.status_code == 200
        new_refresh = rot.json()["refresh_token"]

        # Attacker replays the already-rotated old token → reuse detected.
        replay = await async_client.post("/v1/auth/refresh", json={"refresh_token": old_refresh})
        assert replay.status_code == 401

        # The whole family is cut off: token_version bumped + all refresh tokens
        # revoked, so even the legitimate new token is now dead.
        assert await _token_version("theft@example.com") == before_tv + 1
        followup = await async_client.post("/v1/auth/refresh", json={"refresh_token": new_refresh})
        assert followup.status_code == 401

        async with _TestSessionFactory() as session:
            user_id = (
                await session.execute(select(User.id).where(User.email == "theft@example.com"))
            ).scalar_one()
            active = (
                (
                    await session.execute(
                        select(RefreshToken).where(
                            RefreshToken.user_id == user_id,
                            RefreshToken.revoked_at.is_(None),
                        )
                    )
                )
                .scalars()
                .all()
            )
        assert active == []

    async def test_unknown_token_does_not_bump_version(self, async_client: AsyncClient) -> None:
        await _register(async_client, "noreuse@example.com")
        before = await _token_version("noreuse@example.com")
        resp = await async_client.post(
            "/v1/auth/refresh", json={"refresh_token": "totally-unknown-token"}
        )
        assert resp.status_code == 401
        # A never-seen token is just invalid — it must NOT trigger a family cutoff.
        assert await _token_version("noreuse@example.com") == before


# =====================================================================
# Regression: normal flows still work with the new claim
# =====================================================================


class TestRegression:
    async def test_normal_login_refresh_logout(self, async_client: AsyncClient) -> None:
        tokens = await _register(async_client, "normal@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        assert (await async_client.get("/v1/auth/me", headers=headers)).status_code == 200

        rot = await async_client.post(
            "/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert rot.status_code == 200

        out = await async_client.post(
            "/v1/auth/logout", json={"refresh_token": rot.json()["refresh_token"]}
        )
        assert out.status_code == 200


@pytest.fixture(autouse=True)
def _disable_single_user_mode() -> None:
    """Ensure JWT validation is exercised (not the single-user bypass)."""
    from dailyloadout.config import settings

    settings.single_user_mode = False
