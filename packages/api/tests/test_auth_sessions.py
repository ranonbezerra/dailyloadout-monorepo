"""Session (device) management: list active sessions + revoke one by handle."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

_EMAIL = "test@example.com"
_PASSWORD = "StrongPass123"  # pragma: allowlist secret


async def _login(client: AsyncClient, email: str, password: str) -> dict[str, str]:
    resp = await client.post("/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestSessionListing:
    async def test_lists_active_sessions(
        self, async_client: AsyncClient, register_user: dict[str, Any]
    ) -> None:
        # Registration made one session; a second login makes another.
        await _login(async_client, _EMAIL, _PASSWORD)
        headers = {"Authorization": f"Bearer {register_user['access_token']}"}

        resp = await async_client.get("/v1/auth/sessions", headers=headers)
        assert resp.status_code == 200
        sessions = resp.json()
        assert len(sessions) >= 2
        assert {"public_id", "device_label", "created_at", "expires_at"} <= set(sessions[0])

    async def test_requires_auth(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/v1/auth/sessions")
        assert resp.status_code == 401


class TestSessionRevocation:
    async def test_revoke_removes_the_session(
        self, async_client: AsyncClient, register_user: dict[str, Any]
    ) -> None:
        await _login(async_client, _EMAIL, _PASSWORD)
        headers = {"Authorization": f"Bearer {register_user['access_token']}"}

        before = (await async_client.get("/v1/auth/sessions", headers=headers)).json()
        target = before[0]["public_id"]

        revoked = await async_client.delete(f"/v1/auth/sessions/{target}", headers=headers)
        assert revoked.status_code == 204

        after = (await async_client.get("/v1/auth/sessions", headers=headers)).json()
        assert len(after) == len(before) - 1
        assert target not in {s["public_id"] for s in after}

    async def test_revoke_unknown_session_is_404(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await async_client.delete(
            "/v1/auth/sessions/00000000-0000-0000-0000-000000000000", headers=auth_headers
        )
        assert resp.status_code == 404

    async def test_cannot_revoke_another_users_session(
        self, async_client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        # Register a second user and grab one of THEIR session handles.
        await async_client.post(
            "/v1/auth/register",
            json={"email": "other@example.com", "password": _PASSWORD, "display_name": "Other"},
        )
        other_headers = await _login(async_client, "other@example.com", _PASSWORD)
        other_sessions = (
            await async_client.get("/v1/auth/sessions", headers=other_headers)
        ).json()
        other_handle = other_sessions[0]["public_id"]

        # The first user must not be able to revoke it (owner-scoped → 404, not 403 leak).
        resp = await async_client.delete(f"/v1/auth/sessions/{other_handle}", headers=auth_headers)
        assert resp.status_code == 404
        # ...and it's still active for its owner.
        still = (await async_client.get("/v1/auth/sessions", headers=other_headers)).json()
        assert other_handle in {s["public_id"] for s in still}
