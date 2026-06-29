"""Cross-user data isolation tests.

Verifies that User A cannot access, modify, or delete User B's data.
Each test registers two independent users and asserts that one user's
resources are invisible (404) to the other.
"""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

# =====================================================================
# Helpers
# =====================================================================

_USER_A = {
    "email": "user_a@example.com",
    "password": "StrongPass123",
    "display_name": "User A",
}

_USER_B = {
    "email": "user_b@example.com",
    "password": "StrongPass123",
    "display_name": "User B",
}


async def _register_and_get_headers(
    client: AsyncClient,
    user_data: dict[str, str],
) -> dict[str, str]:
    """Register a user and return Authorization headers."""
    resp = await client.post("/v1/auth/register", json=user_data)
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_game(
    client: AsyncClient,
    headers: dict[str, str],
    slug: str = "elden-ring",
    title: str = "Elden Ring",
) -> dict[str, Any]:
    """Create a game and return the response body."""
    resp = await client.post(
        "/v1/games",
        json={
            "slug": slug,
            "title": title,
            "metadata_source": "manual",
            "summary": "An action RPG.",
            "genres": ["action", "rpg"],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _add_to_library(
    client: AsyncClient,
    headers: dict[str, str],
    game_public_id: str,
    platform_id: int,
    status: str = "backlog",
) -> dict[str, Any]:
    """Add a game to the user's library and return the response body."""
    resp = await client.post(
        "/v1/library",
        json={
            "game_public_id": game_public_id,
            "platform_ids": [platform_id],
            "status": status,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    # The grouped POST returns the game group; callers expect a single entry,
    # so unwrap the one platform state created here.
    return resp.json()["platforms"][0]


async def _create_capture(
    client: AsyncClient,
    headers: dict[str, str],
    raw_text: str = "I bought Hollow Knight",
) -> dict[str, Any]:
    """Submit a text capture and return the response body with candidates."""
    resp = await client.post(
        "/v1/captures/text",
        json={"raw_text": raw_text},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _start_play_session(
    client: AsyncClient,
    headers: dict[str, str],
    entry_public_id: str,
) -> dict[str, Any]:
    """Start a play_session and return the response body."""
    resp = await client.post(
        "/v1/play-sessions",
        json={"library_entry_public_id": entry_public_id},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_library_entry_via_capture(
    client: AsyncClient,
    headers: dict[str, str],
    seed_platforms: list[dict[str, Any]],
    game_text: str = "I bought Hollow Knight",
) -> dict[str, Any]:
    """Submit a capture, confirm the candidate, and return the library entry."""
    capture = await _create_capture(client, headers, raw_text=game_text)
    candidate = capture["candidates"][0]
    platform_id = seed_platforms[0]["id"]

    resp = await client.post(
        f"/v1/captures/{capture['public_id']}/candidates/{candidate['public_id']}/confirm",
        json={"platform_id": platform_id, "status": "playing"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


# =====================================================================
# Library isolation
# =====================================================================


class TestLibraryIsolation:
    """User A's library entries must be invisible to User B."""

    async def test_user_b_cannot_get_user_a_library_entry_via_patch(
        self,
        async_client: AsyncClient,
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """PATCH on User A's library entry should return 404 for User B."""
        headers_a = await _register_and_get_headers(async_client, _USER_A)
        headers_b = await _register_and_get_headers(async_client, _USER_B)

        game = await _create_game(async_client, headers_a)
        entry = await _add_to_library(
            async_client, headers_a, game["public_id"], seed_platforms[0]["id"]
        )

        resp = await async_client.patch(
            f"/v1/library/{entry['public_id']}",
            json={"status": "completed"},
            headers=headers_b,
        )
        assert resp.status_code == 404

    async def test_user_b_cannot_delete_user_a_library_entry(
        self,
        async_client: AsyncClient,
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """DELETE on User A's library entry should return 404 for User B."""
        headers_a = await _register_and_get_headers(async_client, _USER_A)
        headers_b = await _register_and_get_headers(async_client, _USER_B)

        game = await _create_game(async_client, headers_a)
        entry = await _add_to_library(
            async_client, headers_a, game["public_id"], seed_platforms[0]["id"]
        )

        resp = await async_client.delete(
            f"/v1/library/{entry['public_id']}",
            headers=headers_b,
        )
        assert resp.status_code == 404

        # Verify User A's entry still exists.
        resp_check = await async_client.get("/v1/library", headers=headers_a)
        assert resp_check.status_code == 200
        assert resp_check.json()["total"] == 1

    async def test_user_b_delete_does_not_affect_user_a_data(
        self,
        async_client: AsyncClient,
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """After User B's failed delete, User A can still access and modify."""
        headers_a = await _register_and_get_headers(async_client, _USER_A)
        headers_b = await _register_and_get_headers(async_client, _USER_B)

        game = await _create_game(async_client, headers_a)
        entry = await _add_to_library(
            async_client, headers_a, game["public_id"], seed_platforms[0]["id"]
        )

        # User B attempts delete -- should fail.
        await async_client.delete(
            f"/v1/library/{entry['public_id']}",
            headers=headers_b,
        )

        # User A can still update.
        resp = await async_client.patch(
            f"/v1/library/{entry['public_id']}",
            json={"status": "playing"},
            headers=headers_a,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "playing"


# =====================================================================
# Library listing isolation
# =====================================================================


class TestLibraryListingIsolation:
    """User A's library entries must not appear in User B's list."""

    async def test_user_a_entries_not_in_user_b_list(
        self,
        async_client: AsyncClient,
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        headers_a = await _register_and_get_headers(async_client, _USER_A)
        headers_b = await _register_and_get_headers(async_client, _USER_B)

        game = await _create_game(async_client, headers_a)
        await _add_to_library(async_client, headers_a, game["public_id"], seed_platforms[0]["id"])

        # User A should see 1 entry.
        resp_a = await async_client.get("/v1/library", headers=headers_a)
        assert resp_a.status_code == 200
        assert resp_a.json()["total"] == 1

        # User B should see 0 entries.
        resp_b = await async_client.get("/v1/library", headers=headers_b)
        assert resp_b.status_code == 200
        assert resp_b.json()["total"] == 0
        assert resp_b.json()["items"] == []

    async def test_both_users_see_only_own_entries(
        self,
        async_client: AsyncClient,
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Each user adds a game; each only sees their own entry."""
        headers_a = await _register_and_get_headers(async_client, _USER_A)
        headers_b = await _register_and_get_headers(async_client, _USER_B)

        game_a = await _create_game(async_client, headers_a, slug="game-a", title="Game A")
        game_b = await _create_game(async_client, headers_b, slug="game-b", title="Game B")

        entry_a = await _add_to_library(
            async_client, headers_a, game_a["public_id"], seed_platforms[0]["id"]
        )
        entry_b = await _add_to_library(
            async_client, headers_b, game_b["public_id"], seed_platforms[0]["id"]
        )

        # User A sees only their entry (grouped: one game, its platform state).
        resp_a = await async_client.get("/v1/library", headers=headers_a)
        assert resp_a.json()["total"] == 1
        state_a = resp_a.json()["items"][0]["platforms"][0]
        assert state_a["public_id"] == entry_a["public_id"]

        # User B sees only their entry.
        resp_b = await async_client.get("/v1/library", headers=headers_b)
        assert resp_b.json()["total"] == 1
        state_b = resp_b.json()["items"][0]["platforms"][0]
        assert state_b["public_id"] == entry_b["public_id"]


# =====================================================================
# Capture isolation
# =====================================================================


class TestCaptureIsolation:
    """User A's captures and candidates must be invisible to User B."""

    async def test_user_b_cannot_get_user_a_capture(
        self,
        async_client: AsyncClient,
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """GET on User A's capture should return 404 for User B."""
        headers_a = await _register_and_get_headers(async_client, _USER_A)
        headers_b = await _register_and_get_headers(async_client, _USER_B)

        capture = await _create_capture(async_client, headers_a)

        resp = await async_client.get(
            f"/v1/captures/{capture['public_id']}",
            headers=headers_b,
        )
        assert resp.status_code == 404

    async def test_user_b_cannot_confirm_user_a_candidate(
        self,
        async_client: AsyncClient,
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Confirming User A's candidate should return 404 for User B."""
        headers_a = await _register_and_get_headers(async_client, _USER_A)
        headers_b = await _register_and_get_headers(async_client, _USER_B)

        capture = await _create_capture(async_client, headers_a)
        candidate = capture["candidates"][0]

        resp = await async_client.post(
            f"/v1/captures/{capture['public_id']}/candidates/{candidate['public_id']}/confirm",
            json={"platform_id": seed_platforms[0]["id"], "status": "playing"},
            headers=headers_b,
        )
        assert resp.status_code == 404

    async def test_user_b_cannot_reject_user_a_candidate(
        self,
        async_client: AsyncClient,
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Rejecting User A's candidate should return 404 for User B."""
        headers_a = await _register_and_get_headers(async_client, _USER_A)
        headers_b = await _register_and_get_headers(async_client, _USER_B)

        capture = await _create_capture(async_client, headers_a)
        candidate = capture["candidates"][0]

        resp = await async_client.post(
            f"/v1/captures/{capture['public_id']}/candidates/{candidate['public_id']}/reject",
            headers=headers_b,
        )
        assert resp.status_code == 404

    async def test_user_a_captures_not_in_user_b_list(
        self,
        async_client: AsyncClient,
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """User A's captures must not appear in User B's capture list."""
        headers_a = await _register_and_get_headers(async_client, _USER_A)
        headers_b = await _register_and_get_headers(async_client, _USER_B)

        await _create_capture(async_client, headers_a)

        # User A should see 1 capture.
        resp_a = await async_client.get("/v1/captures", headers=headers_a)
        assert resp_a.status_code == 200
        assert resp_a.json()["total"] == 1

        # User B should see 0 captures.
        resp_b = await async_client.get("/v1/captures", headers=headers_b)
        assert resp_b.status_code == 200
        assert resp_b.json()["total"] == 0


# =====================================================================
# PlaySession isolation
# =====================================================================


class TestPlaySessionIsolation:
    """User A's play_sessions must be invisible to User B."""

    async def test_user_b_cannot_get_user_a_play_session(
        self,
        async_client: AsyncClient,
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """GET on User A's play_session should return 404 for User B."""
        headers_a = await _register_and_get_headers(async_client, _USER_A)
        headers_b = await _register_and_get_headers(async_client, _USER_B)

        entry = await _create_library_entry_via_capture(async_client, headers_a, seed_platforms)
        play_session = await _start_play_session(async_client, headers_a, entry["public_id"])

        resp = await async_client.get(
            f"/v1/play-sessions/{play_session['public_id']}",
            headers=headers_b,
        )
        assert resp.status_code == 404

    async def test_user_b_cannot_wrap_up_user_a_play_session(
        self,
        async_client: AsyncClient,
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Submitting a wrap_up on User A's play_session should return 404 for User B."""
        headers_a = await _register_and_get_headers(async_client, _USER_A)
        headers_b = await _register_and_get_headers(async_client, _USER_B)

        entry = await _create_library_entry_via_capture(async_client, headers_a, seed_platforms)
        play_session = await _start_play_session(async_client, headers_a, entry["public_id"])

        resp = await async_client.patch(
            f"/v1/play-sessions/{play_session['public_id']}/wrap-up",
            json={"wrap_up_text": "Attempted cross-user wrap_up."},
            headers=headers_b,
        )
        assert resp.status_code == 404

    async def test_user_b_cannot_end_user_a_play_session(
        self,
        async_client: AsyncClient,
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Ending User A's play_session should return 404 for User B."""
        headers_a = await _register_and_get_headers(async_client, _USER_A)
        headers_b = await _register_and_get_headers(async_client, _USER_B)

        entry = await _create_library_entry_via_capture(async_client, headers_a, seed_platforms)
        play_session = await _start_play_session(async_client, headers_a, entry["public_id"])

        resp = await async_client.post(
            f"/v1/play-sessions/{play_session['public_id']}/end",
            json={"ended_via": "paused_app"},
            headers=headers_b,
        )
        assert resp.status_code == 404

    async def test_user_a_active_play_session_not_visible_to_user_b(
        self,
        async_client: AsyncClient,
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """User B's active-play_session endpoint must not return User A's play_session."""
        headers_a = await _register_and_get_headers(async_client, _USER_A)
        headers_b = await _register_and_get_headers(async_client, _USER_B)

        entry = await _create_library_entry_via_capture(async_client, headers_a, seed_platforms)
        await _start_play_session(async_client, headers_a, entry["public_id"])

        # User B should have no active play_session.
        resp = await async_client.get("/v1/play-sessions/active", headers=headers_b)
        assert resp.status_code == 200
        assert resp.json() is None

    async def test_user_a_play_sessions_not_in_user_b_list(
        self,
        async_client: AsyncClient,
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """User A's play_sessions must not appear in User B's play_session list."""
        headers_a = await _register_and_get_headers(async_client, _USER_A)
        headers_b = await _register_and_get_headers(async_client, _USER_B)

        entry = await _create_library_entry_via_capture(async_client, headers_a, seed_platforms)
        await _start_play_session(async_client, headers_a, entry["public_id"])

        # User A should see 1 play_session.
        resp_a = await async_client.get("/v1/play-sessions", headers=headers_a)
        assert resp_a.status_code == 200
        assert resp_a.json()["total"] == 1

        # User B should see 0 play_sessions.
        resp_b = await async_client.get("/v1/play-sessions", headers=headers_b)
        assert resp_b.status_code == 200
        assert resp_b.json()["total"] == 0

    async def test_user_b_cannot_regenerate_user_a_recap(
        self,
        async_client: AsyncClient,
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Regenerating User A's recap should return 404 for User B."""
        headers_a = await _register_and_get_headers(async_client, _USER_A)
        headers_b = await _register_and_get_headers(async_client, _USER_B)

        entry = await _create_library_entry_via_capture(async_client, headers_a, seed_platforms)
        play_session = await _start_play_session(async_client, headers_a, entry["public_id"])

        resp = await async_client.post(
            f"/v1/play-sessions/{play_session['public_id']}/recap/regenerate",
            headers=headers_b,
        )
        assert resp.status_code == 404

    async def test_cross_user_play_session_ops_leave_original_intact(
        self,
        async_client: AsyncClient,
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Failed cross-user operations must not modify User A's play_session."""
        headers_a = await _register_and_get_headers(async_client, _USER_A)
        headers_b = await _register_and_get_headers(async_client, _USER_B)

        entry = await _create_library_entry_via_capture(async_client, headers_a, seed_platforms)
        play_session = await _start_play_session(async_client, headers_a, entry["public_id"])

        # User B tries wrap_up, end, and regenerate -- all should fail.
        await async_client.patch(
            f"/v1/play-sessions/{play_session['public_id']}/wrap-up",
            json={"wrap_up_text": "cross-user wrap_up attempt"},
            headers=headers_b,
        )
        await async_client.post(
            f"/v1/play-sessions/{play_session['public_id']}/end",
            json={"ended_via": "paused_app"},
            headers=headers_b,
        )
        await async_client.post(
            f"/v1/play-sessions/{play_session['public_id']}/recap/regenerate",
            headers=headers_b,
        )

        # User A's play_session should still be active and unmodified.
        resp = await async_client.get(
            f"/v1/play-sessions/{play_session['public_id']}",
            headers=headers_a,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ended_at"] is None
        assert data["wrap_up_text"] is None
        assert data["ended_via"] is None
