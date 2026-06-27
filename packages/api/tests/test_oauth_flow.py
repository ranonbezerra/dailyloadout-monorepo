"""Integration tests for the OAuth login flow: resolve/link/create + routes."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from dailyloadout.api.v1 import auth_oauth
from dailyloadout.config import settings
from dailyloadout.core.auth.security import hash_password
from dailyloadout.core.auth.service import AuthService
from dailyloadout.infrastructure.db.repositories.oauth import OAuthIdentityRepository
from dailyloadout.infrastructure.db.repositories.refresh_token import RefreshTokenRepository
from dailyloadout.infrastructure.db.repositories.user import UserRepository
from dailyloadout.infrastructure.oauth import (
    OAuthAccountConflictError,
    OAuthError,
    OAuthState,
    OAuthUserInfo,
)
from tests.conftest import _TestSessionFactory


def _info(
    *,
    uid: str = "p-1",
    email: str | None = "social@example.com",
    verified: bool = True,
) -> OAuthUserInfo:
    return OAuthUserInfo(
        provider_uid=uid,
        email=email,
        email_verified=verified,
        display_name="Social User",
        avatar_url="https://cdn/x.png",
    )


async def _resolve(session, provider: str, info: OAuthUserInfo):  # type: ignore[no-untyped-def]
    service = AuthService(
        UserRepository(session),
        RefreshTokenRepository(session),
        oauth_repo=OAuthIdentityRepository(session),
    )
    return await service.oauth_resolve_user(provider, info)


# ── service: oauth_resolve_user ─────────────────────────────────────────


class TestResolveUser:
    async def test_creates_new_passwordless_user(self) -> None:
        async with _TestSessionFactory() as session:
            user, access, refresh = await _resolve(session, "google", _info())
            assert user.password_hash is None
            assert user.email == "social@example.com"
            assert user.email_verified is True
            assert user.avatar_url == "https://cdn/x.png"
            assert access and refresh
            # The identity row was linked.
            identity = await OAuthIdentityRepository(session).get_by_provider_uid("google", "p-1")
            assert identity is not None
            assert identity.user_id == user.id

    async def test_existing_identity_logs_in_same_user(self) -> None:
        async with _TestSessionFactory() as session:
            first, _, _ = await _resolve(session, "google", _info())
            await session.commit()
        async with _TestSessionFactory() as session:
            second, _, _ = await _resolve(session, "google", _info())
            assert second.id == first.id
            # No duplicate user was created.
            assert await UserRepository(session).get_by_email("social@example.com") is not None

    async def test_verified_email_links_to_existing_account(self) -> None:
        async with _TestSessionFactory() as session:
            existing = await UserRepository(session).create(
                "social@example.com", hash_password("Pw123456"), "Pwd User", email_verified=False
            )
            await session.commit()
            existing_id = existing.id
        async with _TestSessionFactory() as session:
            user, _, _ = await _resolve(session, "google", _info(verified=True))
            assert user.id == existing_id
            # Linking a verified provider email also verifies the account.
            assert user.email_verified is True
            identity = await OAuthIdentityRepository(session).get_by_provider_uid("google", "p-1")
            assert identity is not None and identity.user_id == existing_id

    async def test_unverified_email_collision_is_rejected(self) -> None:
        async with _TestSessionFactory() as session:
            await UserRepository(session).create(
                "social@example.com", hash_password("Pw123456"), "Pwd User", email_verified=True
            )
            await session.commit()
        async with _TestSessionFactory() as session:
            with pytest.raises(OAuthAccountConflictError):
                await _resolve(session, "twitch", _info(verified=False))

    async def test_unverified_email_no_account_creates_unverified(self) -> None:
        async with _TestSessionFactory() as session:
            user, _, _ = await _resolve(session, "twitch", _info(uid="t-9", verified=False))
            assert user.email_verified is False

    async def test_missing_email_raises(self) -> None:
        async with _TestSessionFactory() as session:
            with pytest.raises(OAuthError):
                await _resolve(session, "twitch", _info(email=None))


# ── routes: /start and /callback ────────────────────────────────────────


class TestOAuthRoutes:
    async def test_start_redirects_to_provider(
        self, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "google_oauth_client_id", "gid")

        async def _fake_store(state: str, data: OAuthState) -> None:
            return None

        monkeypatch.setattr(auth_oauth, "store_state", _fake_store)
        resp = await async_client.get("/v1/auth/oauth/google/start")
        assert resp.status_code == 302
        location = resp.headers["location"]
        assert location.startswith("https://accounts.google.com")
        assert "code_challenge_method=S256" in location
        assert "client_id=gid" in location

    async def test_start_unconfigured_provider_404(
        self, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "google_oauth_client_id", "")
        resp = await async_client.get("/v1/auth/oauth/google/start")
        assert resp.status_code == 404

    async def test_callback_happy_path_sets_cookie(
        self, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "google_oauth_client_id", "gid")

        async def _fake_consume(state: str) -> OAuthState | None:
            return OAuthState(provider="google", code_verifier="v")

        async def _fake_exchange(provider, code, verifier, redirect_uri):  # type: ignore[no-untyped-def]
            return _info(uid="cb-1", email="cb@example.com")

        monkeypatch.setattr(auth_oauth, "consume_state", _fake_consume)
        monkeypatch.setattr(auth_oauth, "exchange_code_for_user", _fake_exchange)

        resp = await async_client.get("/v1/auth/oauth/google/callback?state=s&code=c")
        assert resp.status_code == 302
        assert resp.headers["location"] == settings.oauth_web_success_url
        assert settings.auth_cookie_name in resp.headers.get("set-cookie", "")

    async def test_callback_invalid_state_redirects_error(
        self, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def _fake_consume(state: str) -> OAuthState | None:
            return None

        monkeypatch.setattr(auth_oauth, "consume_state", _fake_consume)
        resp = await async_client.get("/v1/auth/oauth/google/callback?state=s&code=c")
        assert resp.status_code == 302
        assert "error=invalid_state" in resp.headers["location"]

    async def test_callback_provider_unavailable_redirects_error(
        self, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Valid state, but the provider is no longer configured at callback time.
        monkeypatch.setattr(settings, "google_oauth_client_id", "")

        async def _fake_consume(state: str) -> OAuthState | None:
            return OAuthState(provider="google", code_verifier="v")

        monkeypatch.setattr(auth_oauth, "consume_state", _fake_consume)
        resp = await async_client.get("/v1/auth/oauth/google/callback?state=s&code=c")
        assert resp.status_code == 302
        assert "error=provider_unavailable" in resp.headers["location"]

    async def test_callback_exchange_failure_redirects_error(
        self, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "google_oauth_client_id", "gid")

        async def _fake_consume(state: str) -> OAuthState | None:
            return OAuthState(provider="google", code_verifier="v")

        async def _fake_exchange(provider, code, verifier, redirect_uri):  # type: ignore[no-untyped-def]
            raise OAuthError("provider down")

        monkeypatch.setattr(auth_oauth, "consume_state", _fake_consume)
        monkeypatch.setattr(auth_oauth, "exchange_code_for_user", _fake_exchange)
        resp = await async_client.get("/v1/auth/oauth/google/callback?state=s&code=c")
        assert resp.status_code == 302
        assert "error=oauth_failed" in resp.headers["location"]

    async def test_callback_conflict_redirects_account_exists(
        self, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "twitch_oauth_client_id", "tid")
        # Seed a verified password account that an unverified provider email hits.
        async with _TestSessionFactory() as session:
            await UserRepository(session).create(
                "clash@example.com", hash_password("Pw123456"), "Clash", email_verified=True
            )
            await session.commit()

        async def _fake_consume(state: str) -> OAuthState | None:
            return OAuthState(provider="twitch", code_verifier="v")

        async def _fake_exchange(provider, code, verifier, redirect_uri):  # type: ignore[no-untyped-def]
            return _info(uid="cl-1", email="clash@example.com", verified=False)

        monkeypatch.setattr(auth_oauth, "consume_state", _fake_consume)
        monkeypatch.setattr(auth_oauth, "exchange_code_for_user", _fake_exchange)

        resp = await async_client.get("/v1/auth/oauth/twitch/callback?state=s&code=c")
        assert resp.status_code == 302
        assert "error=account_exists" in resp.headers["location"]
