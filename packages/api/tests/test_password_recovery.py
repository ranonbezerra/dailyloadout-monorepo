"""Password-recovery tests: forgot, reset, and change password.

Covers the signed reset-token helpers, the neutral (no-oracle) forgot flow, the
reset flow's full session cutoff (token_version bump + refresh revoke), and the
authenticated change flow that reissues tokens while killing other sessions.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from slate.core.auth.security import (
    create_email_verification_token,
    create_password_reset_token,
    decode_password_reset_token,
)
from slate.infrastructure.db.models import User
from tests.conftest import _TestSessionFactory

_PASSWORD = "StrongPass123"  # pragma: allowlist secret
_NEW_PASSWORD = "FreshPass456"  # pragma: allowlist secret
_WRONG_PASSWORD = "WrongPass123"  # pragma: allowlist secret
_WEAK_PASSWORD = "weak"  # pragma: allowlist secret — fails the complexity gate


async def _get_user(email: str) -> User:
    async with _TestSessionFactory() as session:
        result = await session.execute(select(User).where(User.email == email))
        return result.scalar_one()


async def _reset_token_for(email: str) -> str:
    user = await _get_user(email)
    return create_password_reset_token(str(user.public_id), user.token_version)


# =====================================================================
# Reset-token helpers
# =====================================================================


class TestResetTokenHelpers:
    def test_token_roundtrip(self) -> None:
        token = create_password_reset_token("the-subject", 7)
        assert decode_password_reset_token(token) == ("the-subject", 7)

    def test_decode_rejects_garbage(self) -> None:
        with pytest.raises(ValueError, match="Invalid or expired reset token"):
            decode_password_reset_token("not-a-jwt")

    def test_decode_rejects_other_purpose(self) -> None:
        """An email-verification token must not be accepted as a reset token."""
        verify_token = create_email_verification_token("some-uuid")
        with pytest.raises(ValueError, match="Invalid or expired reset token"):
            decode_password_reset_token(verify_token)


# =====================================================================
# Forgot password (neutral, no account oracle)
# =====================================================================


class TestForgotPassword:
    async def test_neutral_for_unknown_email(self, async_client: AsyncClient) -> None:
        resp = await async_client.post(
            "/v1/auth/forgot-password",
            json={"email": "ghost@example.com"},
        )
        assert resp.status_code == 200
        assert "reset email was sent" in resp.json()["message"]

    async def test_neutral_for_known_email(
        self, async_client: AsyncClient, register_user: dict[str, str]
    ) -> None:
        resp = await async_client.post(
            "/v1/auth/forgot-password",
            json={"email": "test@example.com"},
        )
        assert resp.status_code == 200
        assert "reset email was sent" in resp.json()["message"]

    async def test_rejects_invalid_email(self, async_client: AsyncClient) -> None:
        resp = await async_client.post(
            "/v1/auth/forgot-password",
            json={"email": "not-an-email"},
        )
        assert resp.status_code == 422


# =====================================================================
# Reset password
# =====================================================================


class TestResetPassword:
    async def test_reset_changes_password(
        self, async_client: AsyncClient, register_user: dict[str, str]
    ) -> None:
        token = await _reset_token_for("test@example.com")
        resp = await async_client.post(
            "/v1/auth/reset-password",
            json={"token": token, "new_password": _NEW_PASSWORD},
        )
        assert resp.status_code == 200

        # The old password no longer works; the new one does.
        old = await async_client.post(
            "/v1/auth/login",
            json={"email": "test@example.com", "password": _PASSWORD},
        )
        assert old.status_code == 401
        new = await async_client.post(
            "/v1/auth/login",
            json={"email": "test@example.com", "password": _NEW_PASSWORD},
        )
        assert new.status_code == 200

    async def test_reset_kills_existing_sessions(
        self, async_client: AsyncClient, register_user: dict[str, str]
    ) -> None:
        old_access = register_user["access_token"]
        old_refresh = register_user["refresh_token"]

        token = await _reset_token_for("test@example.com")
        await async_client.post(
            "/v1/auth/reset-password",
            json={"token": token, "new_password": _NEW_PASSWORD},
        )

        # token_version bump invalidates the pre-reset access token...
        me = await async_client.get(
            "/v1/auth/me", headers={"Authorization": f"Bearer {old_access}"}
        )
        assert me.status_code == 401
        # ...and the pre-reset refresh token is revoked.
        refreshed = await async_client.post(
            "/v1/auth/refresh", json={"refresh_token": old_refresh}
        )
        assert refreshed.status_code == 401

    async def test_reset_token_is_single_use(
        self, async_client: AsyncClient, register_user: dict[str, str]
    ) -> None:
        """The same reset link cannot be replayed: applying it bumps token_version,
        so the token's bound ``tv`` no longer matches on a second attempt."""
        token = await _reset_token_for("test@example.com")

        first = await async_client.post(
            "/v1/auth/reset-password",
            json={"token": token, "new_password": _NEW_PASSWORD},
        )
        assert first.status_code == 200

        replay = await async_client.post(
            "/v1/auth/reset-password",
            json={"token": token, "new_password": "EvenNewer789"},  # pragma: allowlist secret
        )
        assert replay.status_code == 400

    async def test_reset_consume_is_atomic_race_safe(
        self, async_client: AsyncClient, register_user: dict[str, str]
    ) -> None:
        """Two concurrent replays both load ``tv=N``; only one may apply.

        Simulates the race: both requests read the user at the same token_version
        and call the conditional consume with the SAME expected version. The first
        applies (bumps to N+1); the second — still holding the stale N — matches
        zero rows and is rejected. Proves single-use is enforced by the atomic
        UPDATE, not a check-then-write.
        """
        from slate.core.auth.security import hash_password
        from slate.infrastructure.db.repositories.user import UserRepository

        user = await _get_user("test@example.com")
        uid, stale_tv = user.id, user.token_version

        async with _TestSessionFactory() as session:
            first = await UserRepository(session).consume_reset_and_set_password(
                user_id=uid,
                password_hash=hash_password(_NEW_PASSWORD),
                expected_token_version=stale_tv,
            )
            await session.commit()
        assert first is True

        async with _TestSessionFactory() as session:
            second = await UserRepository(session).consume_reset_and_set_password(
                user_id=uid,
                password_hash=hash_password("EvenNewer789"),  # pragma: allowlist secret
                expected_token_version=stale_tv,  # the stale version a racer still holds
            )
            await session.commit()
        assert second is False  # rejected — token already consumed

    async def test_reset_token_superseded_by_session_kill(
        self,
        async_client: AsyncClient,
        register_user: dict[str, str],
        auth_headers: dict[str, str],
    ) -> None:
        """A pending reset link is invalidated by any later token_version bump
        (e.g. logout-everywhere), even if it was never used."""
        token = await _reset_token_for("test@example.com")

        # Bump token_version out from under the pending reset link.
        await async_client.post("/v1/auth/logout-all", headers=auth_headers)

        resp = await async_client.post(
            "/v1/auth/reset-password",
            json={"token": token, "new_password": _NEW_PASSWORD},
        )
        assert resp.status_code == 400

    async def test_invalid_token_400(self, async_client: AsyncClient) -> None:
        resp = await async_client.post(
            "/v1/auth/reset-password",
            json={"token": "bogus", "new_password": _NEW_PASSWORD},
        )
        assert resp.status_code == 400

    async def test_unknown_user_400(self, async_client: AsyncClient) -> None:
        token = create_password_reset_token(str(uuid.uuid4()), 0)
        resp = await async_client.post(
            "/v1/auth/reset-password",
            json={"token": token, "new_password": _NEW_PASSWORD},
        )
        assert resp.status_code == 400

    async def test_bad_uuid_subject_400(self, async_client: AsyncClient) -> None:
        token = create_password_reset_token("not-a-uuid", 0)
        resp = await async_client.post(
            "/v1/auth/reset-password",
            json={"token": token, "new_password": _NEW_PASSWORD},
        )
        assert resp.status_code == 400

    async def test_weak_password_422(
        self, async_client: AsyncClient, register_user: dict[str, str]
    ) -> None:
        token = await _reset_token_for("test@example.com")
        resp = await async_client.post(
            "/v1/auth/reset-password",
            json={"token": token, "new_password": _WEAK_PASSWORD},
        )
        assert resp.status_code == 422


# =====================================================================
# Change password (authenticated)
# =====================================================================


class TestChangePassword:
    async def test_change_succeeds_and_reissues_tokens(
        self,
        async_client: AsyncClient,
        register_user: dict[str, str],
        auth_headers: dict[str, str],
    ) -> None:
        resp = await async_client.post(
            "/v1/auth/change-password",
            json={"current_password": _PASSWORD, "new_password": _NEW_PASSWORD},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        new_tokens = resp.json()
        assert new_tokens["access_token"]
        assert new_tokens["refresh_token"]

        # The freshly issued access token works (current device stays signed in).
        me = await async_client.get(
            "/v1/auth/me",
            headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
        )
        assert me.status_code == 200

        # Login now requires the new password.
        old = await async_client.post(
            "/v1/auth/login",
            json={"email": "test@example.com", "password": _PASSWORD},
        )
        assert old.status_code == 401

    async def test_change_kills_other_sessions(
        self,
        async_client: AsyncClient,
        register_user: dict[str, str],
        auth_headers: dict[str, str],
    ) -> None:
        old_access = register_user["access_token"]
        old_refresh = register_user["refresh_token"]

        await async_client.post(
            "/v1/auth/change-password",
            json={"current_password": _PASSWORD, "new_password": _NEW_PASSWORD},
            headers=auth_headers,
        )

        # The pre-change access token and refresh token are both dead.
        me = await async_client.get(
            "/v1/auth/me", headers={"Authorization": f"Bearer {old_access}"}
        )
        assert me.status_code == 401
        refreshed = await async_client.post(
            "/v1/auth/refresh", json={"refresh_token": old_refresh}
        )
        assert refreshed.status_code == 401

    async def test_change_in_cookie_mode_sets_cookie(
        self,
        async_client: AsyncClient,
        register_user: dict[str, str],
        auth_headers: dict[str, str],
    ) -> None:
        resp = await async_client.post(
            "/v1/auth/change-password",
            json={"current_password": _PASSWORD, "new_password": _NEW_PASSWORD},
            headers={**auth_headers, "X-Auth-Mode": "cookie"},
        )
        assert resp.status_code == 200
        # Cookie mode: refresh token rides in the httpOnly cookie, body is empty.
        assert resp.json()["refresh_token"] == ""
        assert "slate_refresh_token" in resp.headers.get("set-cookie", "")

    async def test_wrong_current_password_400(
        self,
        async_client: AsyncClient,
        register_user: dict[str, str],
        auth_headers: dict[str, str],
    ) -> None:
        resp = await async_client.post(
            "/v1/auth/change-password",
            json={"current_password": _WRONG_PASSWORD, "new_password": _NEW_PASSWORD},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    async def test_requires_authentication(self, async_client: AsyncClient) -> None:
        resp = await async_client.post(
            "/v1/auth/change-password",
            json={"current_password": _PASSWORD, "new_password": _NEW_PASSWORD},
        )
        assert resp.status_code == 401

    async def test_weak_new_password_422(
        self,
        async_client: AsyncClient,
        register_user: dict[str, str],
        auth_headers: dict[str, str],
    ) -> None:
        resp = await async_client.post(
            "/v1/auth/change-password",
            json={"current_password": _PASSWORD, "new_password": _WEAK_PASSWORD},
            headers=auth_headers,
        )
        assert resp.status_code == 422
