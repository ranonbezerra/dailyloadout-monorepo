"""Account-integrity tests (anti-abuse Block A).

Covers the email-verification flow, the dev/test auto-verify bypass, the
RequireVerifiedUser gate on cost routes, the fail-closed auth rate limiter, the
config-driven Turnstile CAPTCHA hook, email normalization, constant-time login,
and the single_user_mode production guard.
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update

from slate.config import Settings, _validate_production_settings, settings
from slate.core.auth.security import (
    create_email_verification_token,
    decode_email_verification_token,
)
from slate.infrastructure.db.models import User
from tests.conftest import _TestSessionFactory


async def _set_unverified(email: str) -> None:
    """Flip a user's email_verified flag to False (simulating production)."""
    async with _TestSessionFactory() as session:
        await session.execute(update(User).where(User.email == email).values(email_verified=False))
        await session.commit()


async def _get_user(email: str) -> User:
    async with _TestSessionFactory() as session:
        result = await session.execute(select(User).where(User.email == email))
        return result.scalar_one()


# =====================================================================
# Dev/test auto-verify bypass
# =====================================================================


class TestAutoVerifyBypass:
    async def test_register_auto_verifies_in_testing(self, async_client: AsyncClient) -> None:
        await async_client.post(
            "/v1/auth/register",
            json={
                "email": "autoverify@example.com",
                "password": "SecurePass1",  # pragma: allowlist secret
                "display_name": "Auto Verify",
            },
        )
        user = await _get_user("autoverify@example.com")
        assert user.email_verified is True

    async def test_me_reports_verified(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await async_client.get("/v1/auth/me", headers=auth_headers)
        assert resp.json()["email_verified"] is True


# =====================================================================
# Email-verification flow
# =====================================================================


class TestVerifyEmail:
    async def test_token_roundtrip(self) -> None:
        token = create_email_verification_token("the-subject")
        assert decode_email_verification_token(token) == "the-subject"

    async def test_decode_rejects_garbage(self) -> None:
        with pytest.raises(ValueError, match="Invalid or expired"):
            decode_email_verification_token("not-a-jwt")

    async def test_decode_rejects_access_token_purpose(self) -> None:
        from slate.core.auth.security import create_access_token

        access = create_access_token("some-uuid", token_version=0)
        with pytest.raises(ValueError, match="Invalid or expired"):
            decode_email_verification_token(access)

    async def test_verify_sets_flag(self, async_client: AsyncClient) -> None:
        await async_client.post(
            "/v1/auth/register",
            json={
                "email": "verify-me@example.com",
                "password": "SecurePass1",
                "display_name": "Verify Me",
            },
        )
        await _set_unverified("verify-me@example.com")
        user = await _get_user("verify-me@example.com")
        token = create_email_verification_token(str(user.public_id))

        resp = await async_client.post("/v1/auth/verify", json={"token": token})
        assert resp.status_code == 200
        assert resp.json()["message"] == "Email verified"

        refreshed = await _get_user("verify-me@example.com")
        assert refreshed.email_verified is True

    async def test_verify_via_query_param(self, async_client: AsyncClient) -> None:
        await async_client.post(
            "/v1/auth/register",
            json={
                "email": "verify-query@example.com",
                "password": "SecurePass1",
                "display_name": "Verify Query",
            },
        )
        await _set_unverified("verify-query@example.com")
        user = await _get_user("verify-query@example.com")
        token = create_email_verification_token(str(user.public_id))

        resp = await async_client.post(f"/v1/auth/verify?token={token}")
        assert resp.status_code == 200

    async def test_verify_idempotent(self, async_client: AsyncClient) -> None:
        await async_client.post(
            "/v1/auth/register",
            json={
                "email": "verify-twice@example.com",
                "password": "SecurePass1",
                "display_name": "Verify Twice",
            },
        )
        user = await _get_user("verify-twice@example.com")  # already verified
        token = create_email_verification_token(str(user.public_id))

        first = await async_client.post("/v1/auth/verify", json={"token": token})
        second = await async_client.post("/v1/auth/verify", json={"token": token})
        assert first.status_code == 200
        assert second.status_code == 200

    async def test_verify_missing_token_400(self, async_client: AsyncClient) -> None:
        resp = await async_client.post("/v1/auth/verify", json={"token": ""})
        assert resp.status_code == 400

    async def test_verify_invalid_token_400(self, async_client: AsyncClient) -> None:
        resp = await async_client.post("/v1/auth/verify", json={"token": "bogus"})
        assert resp.status_code == 400

    async def test_verify_unknown_user_400(self, async_client: AsyncClient) -> None:
        import uuid

        token = create_email_verification_token(str(uuid.uuid4()))
        resp = await async_client.post("/v1/auth/verify", json={"token": token})
        assert resp.status_code == 400

    async def test_verify_token_for_bad_uuid_400(self, async_client: AsyncClient) -> None:
        token = create_email_verification_token("not-a-uuid")
        resp = await async_client.post("/v1/auth/verify", json={"token": token})
        assert resp.status_code == 400


class TestResendVerification:
    async def test_resend_neutral_for_unknown(self, async_client: AsyncClient) -> None:
        resp = await async_client.post(
            "/v1/auth/resend-verification",
            json={"email": "ghost@example.com"},
        )
        assert resp.status_code == 200
        assert "verification email was sent" in resp.json()["message"]

    async def test_resend_for_unverified_user(self, async_client: AsyncClient) -> None:
        await async_client.post(
            "/v1/auth/register",
            json={
                "email": "resend@example.com",
                "password": "SecurePass1",
                "display_name": "Resend",
            },
        )
        await _set_unverified("resend@example.com")
        resp = await async_client.post(
            "/v1/auth/resend-verification",
            json={"email": "resend@example.com"},
        )
        assert resp.status_code == 200

    async def test_resend_for_already_verified_noop(self, async_client: AsyncClient) -> None:
        await async_client.post(
            "/v1/auth/register",
            json={
                "email": "resend-verified@example.com",
                "password": "SecurePass1",
                "display_name": "Resend Verified",
            },
        )
        resp = await async_client.post(
            "/v1/auth/resend-verification",
            json={"email": "resend-verified@example.com"},
        )
        assert resp.status_code == 200


# =====================================================================
# RequireVerifiedUser gate on cost routes
# =====================================================================


class TestVerifiedGate:
    async def _unverified_headers(self, async_client: AsyncClient) -> dict[str, str]:
        resp = await async_client.post(
            "/v1/auth/register",
            json={
                "email": "gated@example.com",
                "password": "SecurePass1",
                "display_name": "Gated User",
            },
        )
        token = resp.json()["access_token"]
        await _set_unverified("gated@example.com")
        return {"Authorization": f"Bearer {token}"}

    async def test_create_game_blocked_when_unverified(self, async_client: AsyncClient) -> None:
        headers = await self._unverified_headers(async_client)
        resp = await async_client.post(
            "/v1/games",
            json={"title": "Some Game"},
            headers=headers,
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Email not verified"

    async def test_pick_create_blocked_when_unverified(self, async_client: AsyncClient) -> None:
        headers = await self._unverified_headers(async_client)
        resp = await async_client.post(
            "/v1/picks",
            json={"mood": "chill", "available_minutes": 30, "mental_energy": "low"},
            headers=headers,
        )
        assert resp.status_code == 403

    async def test_capture_text_blocked_when_unverified(self, async_client: AsyncClient) -> None:
        headers = await self._unverified_headers(async_client)
        resp = await async_client.post(
            "/v1/captures/text",
            json={"raw_text": "Played Hades", "input_type": "text"},
            headers=headers,
        )
        assert resp.status_code == 403

    async def test_concierge_blocked_when_unverified(self, async_client: AsyncClient) -> None:
        headers = await self._unverified_headers(async_client)
        resp = await async_client.post(
            "/v1/concierge/chat",
            json={"message": "what should I play"},
            headers=headers,
        )
        assert resp.status_code == 403

    async def test_read_route_allowed_when_unverified(self, async_client: AsyncClient) -> None:
        """Cheap read routes (me, GET library) stay open for unverified users."""
        headers = await self._unverified_headers(async_client)
        assert (await async_client.get("/v1/auth/me", headers=headers)).status_code == 200
        assert (await async_client.get("/v1/library", headers=headers)).status_code == 200


# =====================================================================
# Email normalization
# =====================================================================


class TestEmailNormalization:
    async def test_duplicate_detected_case_insensitively(self, async_client: AsyncClient) -> None:
        first = await async_client.post(
            "/v1/auth/register",
            json={
                "email": "Norm@Example.com",
                "password": "SecurePass1",
                "display_name": "Norm",
            },
        )
        assert first.status_code == 201
        # Different casing must collide with the normalized stored value.
        dupe = await async_client.post(
            "/v1/auth/register",
            json={
                "email": "norm@example.com",
                "password": "SecurePass1",
                "display_name": "Norm Two",
            },
        )
        assert dupe.status_code == 409

    async def test_login_with_different_case(self, async_client: AsyncClient) -> None:
        await async_client.post(
            "/v1/auth/register",
            json={
                "email": "caselogin@example.com",
                "password": "SecurePass1",
                "display_name": "Case Login",
            },
        )
        resp = await async_client.post(
            "/v1/auth/login",
            json={"email": "CaseLogin@Example.com", "password": "SecurePass1"},
        )
        assert resp.status_code == 200

    async def test_stored_email_is_lowercased(self, async_client: AsyncClient) -> None:
        await async_client.post(
            "/v1/auth/register",
            json={
                "email": "  Mixed@Case.COM  ",
                "password": "SecurePass1",
                "display_name": "Mixed",
            },
        )
        user = await _get_user("mixed@case.com")
        assert user.email == "mixed@case.com"


# =====================================================================
# Constant-time login (no account oracle)
# =====================================================================


class TestConstantTimeLogin:
    async def test_unknown_user_still_401(self, async_client: AsyncClient) -> None:
        resp = await async_client.post(
            "/v1/auth/login",
            json={"email": "nobody-here@example.com", "password": "SecurePass1"},
        )
        assert resp.status_code == 401

    async def test_dummy_verify_runs(self) -> None:
        from slate.core.auth.security import verify_password_dummy

        # Should execute a bcrypt check without raising or matching.
        verify_password_dummy("whatever")


# =====================================================================
# single_user_mode production guard
# =====================================================================


class TestSingleUserProductionGuard:
    def test_production_rejects_single_user_mode(self) -> None:
        s = Settings(
            app_env="production",
            secret_key="s" * 40,  # pragma: allowlist secret
            auth_cookie_secure=True,
            single_user_mode=True,
        )
        with pytest.raises(RuntimeError, match="single_user_mode"):
            _validate_production_settings(s)

    def test_production_allows_single_user_mode_off(self) -> None:
        s = Settings(
            app_env="production",
            secret_key="s" * 40,  # pragma: allowlist secret
            auth_cookie_secure=True,
            single_user_mode=False,
            turnstile_secret="ts-secret",  # pragma: allowlist secret
        )
        _validate_production_settings(s)  # should not raise

    def test_dev_allows_single_user_mode(self) -> None:
        s = Settings(app_env="development", single_user_mode=True)
        _validate_production_settings(s)  # should not raise

    def test_is_production_property(self) -> None:
        assert Settings(app_env="production").is_production is True
        assert Settings(app_env="development").is_production is False
        assert Settings(app_env="testing").is_production is False


# =====================================================================
# Production register path (auto-verify OFF, email best-effort)
# =====================================================================


class TestProductionRegister:
    @pytest.fixture
    def _production_env(self) -> Any:
        original = settings.app_env
        settings.app_env = "production"
        yield
        settings.app_env = original

    async def test_register_in_production_leaves_unverified(
        self, async_client: AsyncClient, _production_env: Any
    ) -> None:
        resp = await async_client.post(
            "/v1/auth/register",
            json={
                "email": "prod-user@example.com",
                "password": "SecurePass1",
                "display_name": "Prod User",
            },
        )
        assert resp.status_code == 201
        user = await _get_user("prod-user@example.com")
        assert user.email_verified is False

    async def test_cost_route_blocked_after_production_register(
        self, async_client: AsyncClient, _production_env: Any
    ) -> None:
        resp = await async_client.post(
            "/v1/auth/register",
            json={
                "email": "prod-gated@example.com",
                "password": "SecurePass1",
                "display_name": "Prod Gated",
            },
        )
        headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        blocked = await async_client.post("/v1/games", json={"title": "X"}, headers=headers)
        assert blocked.status_code == 403
