"""Common-password blocklist: the offline breached-password check."""

from __future__ import annotations

from httpx import AsyncClient

from slate.core.auth.password_breach import is_common_password


class TestBlocklist:
    def test_flags_common_passwords_case_insensitively(self) -> None:
        assert is_common_password("Password123") is True
        assert is_common_password("password123") is True
        assert is_common_password("PASSWORD123") is True
        assert is_common_password("  Welcome2024  ") is True  # trimmed

    def test_allows_non_common_passwords(self) -> None:
        assert is_common_password("StrongPass123") is False
        assert is_common_password("q7$Fbz-Wintermute92") is False


class TestRegistrationRejectsCommon:
    async def test_register_rejects_a_common_password(self, async_client: AsyncClient) -> None:
        # Passes the complexity rules (upper+lower+digit) but is trivially guessable.
        resp = await async_client.post(
            "/v1/auth/register",
            json={
                "email": "common@example.com",
                "password": "Password123",  # pragma: allowlist secret
                "display_name": "Common",
            },
        )
        assert resp.status_code == 422

    async def test_register_accepts_a_strong_password(self, async_client: AsyncClient) -> None:
        resp = await async_client.post(
            "/v1/auth/register",
            json={
                "email": "strong@example.com",
                "password": "q7$Fbz-Wintermute92",  # pragma: allowlist secret
                "display_name": "Strong",
            },
        )
        assert resp.status_code == 201
