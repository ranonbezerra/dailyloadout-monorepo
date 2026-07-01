"""MFA (TOTP) tests: enrollment, login challenge, recovery codes, disable.

Covers the encryption-at-rest helper, the purpose-scoped challenge token, the
full two-factor login exchange, single-use recovery codes, and the management
endpoints (status / enroll / confirm / regenerate / disable).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pyotp
import pytest
from httpx import AsyncClient

from slate.core.auth.security import (
    create_mfa_challenge_token,
    create_password_reset_token,
    decode_mfa_challenge_token,
)
from slate.infrastructure.crypto import decrypt_secret, encrypt_secret

_PASSWORD = "StrongPass123"  # pragma: allowlist secret — matches conftest default user
_EMAIL = "test@example.com"


def _totp_now(secret: str) -> str:
    return pyotp.TOTP(secret).now()


def _totp_next(secret: str) -> str:
    """A code for the NEXT 30s step — valid after the current step was consumed
    (TOTP replay protection rejects re-using the just-confirmed code)."""
    return pyotp.TOTP(secret).at(datetime.now(UTC) + timedelta(seconds=30))


async def _enroll_and_confirm(
    client: AsyncClient, headers: dict[str, str]
) -> tuple[str, list[str]]:
    """Enroll + confirm MFA for the default user; return (secret, recovery_codes)."""
    enroll = await client.post("/v1/auth/mfa/enroll", headers=headers)
    assert enroll.status_code == 200, enroll.text
    secret = enroll.json()["secret"]
    confirm = await client.post(
        "/v1/auth/mfa/confirm", json={"code": _totp_now(secret)}, headers=headers
    )
    assert confirm.status_code == 200, confirm.text
    return secret, confirm.json()["recovery_codes"]


# =====================================================================
# Encryption-at-rest + challenge-token helpers (unit)
# =====================================================================


class TestCryptoAndTokens:
    def test_secret_encryption_roundtrip(self) -> None:
        secret = "JBSWY3DPEHPK3PXP"  # pragma: allowlist secret
        token = encrypt_secret(secret)
        assert token != secret
        assert decrypt_secret(token) == secret

    def test_decrypt_rejects_garbage(self) -> None:
        with pytest.raises(ValueError, match="Could not decrypt"):
            decrypt_secret("not-a-fernet-token")

    def test_challenge_token_roundtrip(self) -> None:
        token = create_mfa_challenge_token("subject-uuid", 3)
        assert decode_mfa_challenge_token(token) == ("subject-uuid", 3)

    def test_challenge_rejects_other_purpose(self) -> None:
        reset = create_password_reset_token("subject-uuid", 0)
        with pytest.raises(ValueError, match="Invalid or expired MFA challenge"):
            decode_mfa_challenge_token(reset)

    def test_challenge_rejects_garbage(self) -> None:
        with pytest.raises(ValueError, match="Invalid or expired MFA challenge"):
            decode_mfa_challenge_token("nope")


# =====================================================================
# Enrollment
# =====================================================================


class TestEnrollment:
    async def test_status_disabled_by_default(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await async_client.get("/v1/auth/mfa/status", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == {"enabled": False, "recovery_codes_remaining": 0}

    async def test_enroll_returns_secret_and_uri(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await async_client.post("/v1/auth/mfa/enroll", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["secret"]
        assert body["otpauth_uri"].startswith("otpauth://totp/")
        assert "Slate" in body["otpauth_uri"]

    async def test_confirm_activates_and_returns_recovery_codes(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        _secret, codes = await _enroll_and_confirm(async_client, auth_headers)
        assert len(codes) == 10

        status = await async_client.get("/v1/auth/mfa/status", headers=auth_headers)
        assert status.json() == {"enabled": True, "recovery_codes_remaining": 10}

    async def test_confirm_with_wrong_code_400(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        await async_client.post("/v1/auth/mfa/enroll", headers=auth_headers)
        resp = await async_client.post(
            "/v1/auth/mfa/confirm", json={"code": "000000"}, headers=auth_headers
        )
        assert resp.status_code == 400

    async def test_confirm_without_enrollment_400(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await async_client.post(
            "/v1/auth/mfa/confirm", json={"code": "000000"}, headers=auth_headers
        )
        assert resp.status_code == 400

    async def test_enroll_when_already_enabled_409(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        await _enroll_and_confirm(async_client, auth_headers)
        resp = await async_client.post("/v1/auth/mfa/enroll", headers=auth_headers)
        assert resp.status_code == 409

    async def test_endpoints_require_auth(self, async_client: AsyncClient) -> None:
        assert (await async_client.get("/v1/auth/mfa/status")).status_code == 401
        assert (await async_client.post("/v1/auth/mfa/enroll")).status_code == 401


# =====================================================================
# Two-factor login
# =====================================================================


class TestMfaLogin:
    async def test_login_returns_challenge_when_enabled(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        await _enroll_and_confirm(async_client, auth_headers)

        login = await async_client.post(
            "/v1/auth/login", json={"email": _EMAIL, "password": _PASSWORD}
        )
        assert login.status_code == 200
        body = login.json()
        assert body["mfa_required"] is True
        assert body["mfa_token"]
        assert body["access_token"] == ""

    async def test_mfa_login_with_totp_issues_tokens(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        secret, _ = await _enroll_and_confirm(async_client, auth_headers)
        login = await async_client.post(
            "/v1/auth/login", json={"email": _EMAIL, "password": _PASSWORD}
        )
        mfa_token = login.json()["mfa_token"]

        resp = await async_client.post(
            "/v1/auth/mfa/login", json={"mfa_token": mfa_token, "code": _totp_next(secret)}
        )
        assert resp.status_code == 200
        access = resp.json()["access_token"]
        assert access
        me = await async_client.get("/v1/auth/me", headers={"Authorization": f"Bearer {access}"})
        assert me.status_code == 200

    async def test_totp_code_cannot_be_replayed(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """A TOTP code accepted once is rejected on reuse within its window."""
        secret, _ = await _enroll_and_confirm(async_client, auth_headers)
        code = _totp_next(secret)

        async def _login_with(c: str) -> int:
            login = await async_client.post(
                "/v1/auth/login", json={"email": _EMAIL, "password": _PASSWORD}
            )
            token = login.json()["mfa_token"]
            resp = await async_client.post(
                "/v1/auth/mfa/login", json={"mfa_token": token, "code": c}
            )
            return resp.status_code

        assert await _login_with(code) == 200  # first use accepted
        assert await _login_with(code) != 200  # same code replayed → rejected

    async def test_mfa_login_with_recovery_code_consumes_it(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        _secret, codes = await _enroll_and_confirm(async_client, auth_headers)
        login = await async_client.post(
            "/v1/auth/login", json={"email": _EMAIL, "password": _PASSWORD}
        )
        mfa_token = login.json()["mfa_token"]

        # First use of the recovery code succeeds.
        first = await async_client.post(
            "/v1/auth/mfa/login", json={"mfa_token": mfa_token, "code": codes[0]}
        )
        assert first.status_code == 200

        status = await async_client.get("/v1/auth/mfa/status", headers=auth_headers)
        assert status.json()["recovery_codes_remaining"] == 9

        # Replaying the same recovery code fails (single-use).
        login2 = await async_client.post(
            "/v1/auth/login", json={"email": _EMAIL, "password": _PASSWORD}
        )
        replay = await async_client.post(
            "/v1/auth/mfa/login",
            json={"mfa_token": login2.json()["mfa_token"], "code": codes[0]},
        )
        assert replay.status_code == 401

    async def test_mfa_login_cookie_mode_sets_cookie(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        secret, _ = await _enroll_and_confirm(async_client, auth_headers)
        login = await async_client.post(
            "/v1/auth/login",
            json={"email": _EMAIL, "password": _PASSWORD},
            headers={"X-Auth-Mode": "cookie"},
        )
        mfa_token = login.json()["mfa_token"]

        resp = await async_client.post(
            "/v1/auth/mfa/login",
            json={"mfa_token": mfa_token, "code": _totp_next(secret)},
            headers={"X-Auth-Mode": "cookie"},
        )
        assert resp.status_code == 200
        assert resp.json()["refresh_token"] == ""
        assert "slate_refresh_token" in resp.headers.get("set-cookie", "")

    async def test_mfa_login_wrong_code_401(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        await _enroll_and_confirm(async_client, auth_headers)
        login = await async_client.post(
            "/v1/auth/login", json={"email": _EMAIL, "password": _PASSWORD}
        )
        resp = await async_client.post(
            "/v1/auth/mfa/login",
            json={"mfa_token": login.json()["mfa_token"], "code": "000000"},
        )
        assert resp.status_code == 401

    async def test_mfa_login_bad_token_401(self, async_client: AsyncClient) -> None:
        resp = await async_client.post(
            "/v1/auth/mfa/login", json={"mfa_token": "garbage", "code": "000000"}
        )
        assert resp.status_code == 401

    async def test_challenge_invalidated_by_session_kill(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        secret, _ = await _enroll_and_confirm(async_client, auth_headers)
        login = await async_client.post(
            "/v1/auth/login", json={"email": _EMAIL, "password": _PASSWORD}
        )
        mfa_token = login.json()["mfa_token"]

        # Bump token_version after the challenge was minted.
        await async_client.post("/v1/auth/logout-all", headers=auth_headers)

        resp = await async_client.post(
            "/v1/auth/mfa/login", json={"mfa_token": mfa_token, "code": _totp_next(secret)}
        )
        assert resp.status_code == 401


# =====================================================================
# Recovery codes + disable
# =====================================================================


class TestRecoveryAndDisable:
    async def test_regenerate_recovery_codes_invalidates_old(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        secret, old_codes = await _enroll_and_confirm(async_client, auth_headers)

        regen = await async_client.post(
            "/v1/auth/mfa/recovery-codes",
            json={"code": _totp_next(secret)},
            headers=auth_headers,
        )
        assert regen.status_code == 200
        new_codes = regen.json()["recovery_codes"]
        assert set(new_codes).isdisjoint(old_codes)

        # An old code no longer works.
        login = await async_client.post(
            "/v1/auth/login", json={"email": _EMAIL, "password": _PASSWORD}
        )
        resp = await async_client.post(
            "/v1/auth/mfa/login",
            json={"mfa_token": login.json()["mfa_token"], "code": old_codes[0]},
        )
        assert resp.status_code == 401

    async def test_regenerate_with_wrong_code_400(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        await _enroll_and_confirm(async_client, auth_headers)
        resp = await async_client.post(
            "/v1/auth/mfa/recovery-codes", json={"code": "000000"}, headers=auth_headers
        )
        assert resp.status_code == 400

    async def test_disable_with_valid_code(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        secret, _ = await _enroll_and_confirm(async_client, auth_headers)

        resp = await async_client.post(
            "/v1/auth/mfa/disable", json={"code": _totp_next(secret)}, headers=auth_headers
        )
        assert resp.status_code == 200

        status = await async_client.get("/v1/auth/mfa/status", headers=auth_headers)
        assert status.json()["enabled"] is False

        # Login no longer requires a second factor.
        login = await async_client.post(
            "/v1/auth/login", json={"email": _EMAIL, "password": _PASSWORD}
        )
        assert login.json()["mfa_required"] is False
        assert login.json()["access_token"]

    async def test_disable_with_wrong_code_400(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        await _enroll_and_confirm(async_client, auth_headers)
        resp = await async_client.post(
            "/v1/auth/mfa/disable", json={"code": "000000"}, headers=auth_headers
        )
        assert resp.status_code == 400

    async def test_disable_when_not_enabled_400(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await async_client.post(
            "/v1/auth/mfa/disable", json={"code": "000000"}, headers=auth_headers
        )
        assert resp.status_code == 400


# =====================================================================
# Non-MFA login is unchanged
# =====================================================================


async def test_login_without_mfa_issues_tokens(
    async_client: AsyncClient, register_user: dict[str, Any]
) -> None:
    login = await async_client.post(
        "/v1/auth/login", json={"email": _EMAIL, "password": _PASSWORD}
    )
    assert login.status_code == 200
    body = login.json()
    assert body["mfa_required"] is False
    assert body["access_token"]
