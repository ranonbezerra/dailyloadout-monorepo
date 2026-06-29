"""Tests for the pick endpoints (v1/picks)."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

# =====================================================================
# Helpers
# =====================================================================


async def _create_library_entry(
    client: AsyncClient,
    headers: dict[str, str],
    seed_platforms: list[dict[str, Any]],
    game_text: str = "I bought Hollow Knight",
) -> dict[str, Any]:
    """Submit a capture, confirm the candidate, and return the library entry."""
    resp = await client.post(
        "/v1/captures/text",
        json={"raw_text": game_text},
        headers=headers,
    )
    assert resp.status_code == 201
    capture = resp.json()

    candidate = capture["candidates"][0]
    platform_id = seed_platforms[0]["id"]

    resp = await client.post(
        f"/v1/captures/{capture['public_id']}/candidates/{candidate['public_id']}/confirm",
        json={"platform_id": platform_id, "status": "playing"},
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


async def _create_pick(
    client: AsyncClient,
    headers: dict[str, str],
    mood: str = "chill",
    available_minutes: int = 60,
    mental_energy: str = "medium",
    count: int = 1,
) -> dict[str, Any]:
    """Create a pick and return the first item from the response list."""
    resp = await client.post(
        "/v1/picks",
        json={
            "mood": mood,
            "available_minutes": available_minutes,
            "mental_energy": mental_energy,
            "count": count,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    items = resp.json()
    assert isinstance(items, list)
    assert len(items) >= 1
    return items[0]


async def _create_picks(
    client: AsyncClient,
    headers: dict[str, str],
    mood: str = "chill",
    available_minutes: int = 60,
    mental_energy: str = "medium",
    count: int = 3,
) -> list[dict[str, Any]]:
    """Create multiple picks and return the full response list."""
    resp = await client.post(
        "/v1/picks",
        json={
            "mood": mood,
            "available_minutes": available_minutes,
            "mental_energy": mental_energy,
            "count": count,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# =====================================================================
# Test: Create pick
# =====================================================================


class TestCreatePick:
    async def test_create_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        await _create_library_entry(async_client, auth_headers, seed_platforms)
        pick = await _create_pick(async_client, auth_headers)

        assert pick["library_entry"] is not None
        assert pick["reasoning"] is not None
        assert pick["action"] is None
        assert pick["mood"] == "chill"
        assert pick["available_minutes"] == 60
        assert pick["mental_energy"] == "medium"

    async def test_create_multiple(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Request 3 suggestions but only 1 game exists → returns 1."""
        await _create_library_entry(async_client, auth_headers, seed_platforms)
        picks = await _create_picks(async_client, auth_headers, count=3)
        # DummyLLMClient always picks the first candidate, and after
        # it's removed from the pool the second call also picks the
        # first remaining — but we only have 1 library entry, so
        # count is capped to 1.
        assert len(picks) == 1

    async def test_create_no_eligible_games(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Pick with no games in library returns 422."""
        resp = await async_client.post(
            "/v1/picks",
            json={
                "mood": "chill",
                "available_minutes": 60,
                "mental_energy": "medium",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_create_unauthorized(
        self,
        async_client: AsyncClient,
    ) -> None:
        resp = await async_client.post(
            "/v1/picks",
            json={
                "mood": "chill",
                "available_minutes": 60,
                "mental_energy": "medium",
            },
        )
        assert resp.status_code == 401


# =====================================================================
# Test: Accept pick
# =====================================================================


class TestStartPick:
    """POST /v1/picks/start — AI-pick + start in one step (Epic 12)."""

    async def _start(
        self,
        client: AsyncClient,
        headers: dict[str, str],
        **extra: Any,
    ) -> Any:
        return await client.post(
            "/v1/picks/start",
            json={"mood": "chill", "available_minutes": 60, "mental_energy": "medium", **extra},
            headers=headers,
        )

    async def test_start_picks_and_starts_play_session(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        await _create_library_entry(async_client, auth_headers, seed_platforms)

        resp = await self._start(async_client, auth_headers)
        assert resp.status_code == 201, resp.text
        assert resp.json()["action"] == "accepted"

        active = (await async_client.get("/v1/play-sessions/active", headers=auth_headers)).json()
        assert active is not None
        assert active["recap_text"] is None

    async def test_start_with_recap(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        await _create_library_entry(async_client, auth_headers, seed_platforms)

        resp = await self._start(async_client, auth_headers, recap_text="Resume at the gate.")
        assert resp.status_code == 201, resp.text

        active = (await async_client.get("/v1/play-sessions/active", headers=auth_headers)).json()
        assert active["recap_text"] == "Resume at the gate."

    async def test_start_no_eligible_games_returns_422(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await self._start(async_client, auth_headers)
        assert resp.status_code == 422

    async def test_start_with_active_play_session_returns_409(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        await _create_library_entry(async_client, auth_headers, seed_platforms)
        assert (await self._start(async_client, auth_headers)).status_code == 201

        # A play_session is now active; a second start must be rejected.
        assert (await self._start(async_client, auth_headers)).status_code == 409


class TestAcceptPick:
    async def test_accept_creates_play_session(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        await _create_library_entry(async_client, auth_headers, seed_platforms)
        pick = await _create_pick(async_client, auth_headers)

        resp = await async_client.post(
            f"/v1/picks/{pick['public_id']}/accept",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        accepted = resp.json()
        assert accepted["action"] == "accepted"

        # Verify a play_session was created.
        resp = await async_client.get("/v1/play-sessions/active", headers=auth_headers)
        assert resp.status_code == 200
        play_session = resp.json()
        assert play_session is not None
        assert play_session["library_entry"]["public_id"] == pick["library_entry"]["public_id"]

    async def test_accept_with_recap_starts_play_session_with_recap(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Accepting a pick can carry a pre-generated recap (Epic 12)."""
        await _create_library_entry(async_client, auth_headers, seed_platforms)
        pick = await _create_pick(async_client, auth_headers)

        resp = await async_client.post(
            f"/v1/picks/{pick['public_id']}/accept",
            headers=auth_headers,
            json={"recap_text": "Previously on your game: you reached the gate."},
        )
        assert resp.status_code == 200
        assert resp.json()["action"] == "accepted"

        resp = await async_client.get("/v1/play-sessions/active", headers=auth_headers)
        play_session = resp.json()
        assert play_session["recap_text"] == "Previously on your game: you reached the gate."

    async def test_accept_already_actioned(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        await _create_library_entry(async_client, auth_headers, seed_platforms)
        pick = await _create_pick(async_client, auth_headers)

        # Accept once.
        resp = await async_client.post(
            f"/v1/picks/{pick['public_id']}/accept",
            headers=auth_headers,
        )
        assert resp.status_code == 200

        # Accept again → 409.
        resp = await async_client.post(
            f"/v1/picks/{pick['public_id']}/accept",
            headers=auth_headers,
        )
        assert resp.status_code == 409

    async def test_accept_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        from uuid import uuid4

        resp = await async_client.post(
            f"/v1/picks/{uuid4()}/accept",
            headers=auth_headers,
        )
        assert resp.status_code == 404


# =====================================================================
# Test: Reject pick
# =====================================================================


class TestRejectPick:
    async def test_reject_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        await _create_library_entry(async_client, auth_headers, seed_platforms)
        pick = await _create_pick(async_client, auth_headers)

        resp = await async_client.post(
            f"/v1/picks/{pick['public_id']}/reject",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        rejected = resp.json()
        assert rejected["action"] == "rejected"

    async def test_reject_already_actioned(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        await _create_library_entry(async_client, auth_headers, seed_platforms)
        pick = await _create_pick(async_client, auth_headers)

        resp = await async_client.post(
            f"/v1/picks/{pick['public_id']}/reject",
            headers=auth_headers,
        )
        assert resp.status_code == 200

        resp = await async_client.post(
            f"/v1/picks/{pick['public_id']}/reject",
            headers=auth_headers,
        )
        assert resp.status_code == 409


# =====================================================================
# Test: UUID reroll validation
# =====================================================================


class TestPickReroll:
    async def test_invalid_uuid_returns_422(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """When DummyLLMClient returns invalid UUIDs
        (mood=test_invalid_uuid), the schema validation rejects the
        mood literal and returns 422.
        """
        await _create_library_entry(async_client, auth_headers, seed_platforms)

        resp = await async_client.post(
            "/v1/picks",
            json={
                "mood": "test_invalid_uuid",
                "available_minutes": 60,
                "mental_energy": "medium",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422


# =====================================================================
# Test: Listing
# =====================================================================


class TestPickListing:
    async def test_list_empty(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await async_client.get("/v1/picks", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_with_picks(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        await _create_library_entry(async_client, auth_headers, seed_platforms)
        await _create_pick(async_client, auth_headers)

        resp = await async_client.get("/v1/picks", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["total"] == 1

    async def test_latest_pending(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        await _create_library_entry(async_client, auth_headers, seed_platforms)
        pick = await _create_pick(async_client, auth_headers)

        resp = await async_client.get("/v1/picks/latest", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["public_id"] == pick["public_id"]

    async def test_latest_none_when_all_actioned(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        await _create_library_entry(async_client, auth_headers, seed_platforms)
        pick = await _create_pick(async_client, auth_headers)

        # Reject it.
        await async_client.post(
            f"/v1/picks/{pick['public_id']}/reject",
            headers=auth_headers,
        )

        resp = await async_client.get("/v1/picks/latest", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() is None
