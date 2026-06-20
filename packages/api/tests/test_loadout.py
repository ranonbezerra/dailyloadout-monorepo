"""Tests for the loadout endpoints (v1/loadouts)."""

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


async def _create_loadout(
    client: AsyncClient,
    headers: dict[str, str],
    mood: str = "chill",
    available_minutes: int = 60,
    mental_energy: str = "medium",
    count: int = 1,
) -> dict[str, Any]:
    """Create a loadout and return the first item from the response list."""
    resp = await client.post(
        "/v1/loadouts",
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


async def _create_loadouts(
    client: AsyncClient,
    headers: dict[str, str],
    mood: str = "chill",
    available_minutes: int = 60,
    mental_energy: str = "medium",
    count: int = 3,
) -> list[dict[str, Any]]:
    """Create multiple loadouts and return the full response list."""
    resp = await client.post(
        "/v1/loadouts",
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
# Test: Create loadout
# =====================================================================


class TestCreateLoadout:
    async def test_create_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        await _create_library_entry(async_client, auth_headers, seed_platforms)
        loadout = await _create_loadout(async_client, auth_headers)

        assert loadout["library_entry"] is not None
        assert loadout["reasoning"] is not None
        assert loadout["action"] is None
        assert loadout["mood"] == "chill"
        assert loadout["available_minutes"] == 60
        assert loadout["mental_energy"] == "medium"

    async def test_create_multiple(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Request 3 suggestions but only 1 game exists → returns 1."""
        await _create_library_entry(async_client, auth_headers, seed_platforms)
        loadouts = await _create_loadouts(async_client, auth_headers, count=3)
        # DummyLLMClient always picks the first candidate, and after
        # it's removed from the pool the second call also picks the
        # first remaining — but we only have 1 library entry, so
        # count is capped to 1.
        assert len(loadouts) == 1

    async def test_create_no_eligible_games(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Loadout with no games in library returns 422."""
        resp = await async_client.post(
            "/v1/loadouts",
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
            "/v1/loadouts",
            json={
                "mood": "chill",
                "available_minutes": 60,
                "mental_energy": "medium",
            },
        )
        assert resp.status_code == 401


# =====================================================================
# Test: Accept loadout
# =====================================================================


class TestAcceptLoadout:
    async def test_accept_creates_mission(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        await _create_library_entry(async_client, auth_headers, seed_platforms)
        loadout = await _create_loadout(async_client, auth_headers)

        resp = await async_client.post(
            f"/v1/loadouts/{loadout['public_id']}/accept",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        accepted = resp.json()
        assert accepted["action"] == "accepted"

        # Verify a mission was created.
        resp = await async_client.get("/v1/missions/active", headers=auth_headers)
        assert resp.status_code == 200
        mission = resp.json()
        assert mission is not None
        assert mission["library_entry"]["public_id"] == loadout["library_entry"]["public_id"]

    async def test_accept_already_actioned(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        await _create_library_entry(async_client, auth_headers, seed_platforms)
        loadout = await _create_loadout(async_client, auth_headers)

        # Accept once.
        resp = await async_client.post(
            f"/v1/loadouts/{loadout['public_id']}/accept",
            headers=auth_headers,
        )
        assert resp.status_code == 200

        # Accept again → 409.
        resp = await async_client.post(
            f"/v1/loadouts/{loadout['public_id']}/accept",
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
            f"/v1/loadouts/{uuid4()}/accept",
            headers=auth_headers,
        )
        assert resp.status_code == 404


# =====================================================================
# Test: Reject loadout
# =====================================================================


class TestRejectLoadout:
    async def test_reject_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        await _create_library_entry(async_client, auth_headers, seed_platforms)
        loadout = await _create_loadout(async_client, auth_headers)

        resp = await async_client.post(
            f"/v1/loadouts/{loadout['public_id']}/reject",
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
        loadout = await _create_loadout(async_client, auth_headers)

        resp = await async_client.post(
            f"/v1/loadouts/{loadout['public_id']}/reject",
            headers=auth_headers,
        )
        assert resp.status_code == 200

        resp = await async_client.post(
            f"/v1/loadouts/{loadout['public_id']}/reject",
            headers=auth_headers,
        )
        assert resp.status_code == 409


# =====================================================================
# Test: UUID reroll validation
# =====================================================================


class TestLoadoutReroll:
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
            "/v1/loadouts",
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


class TestLoadoutListing:
    async def test_list_empty(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await async_client.get("/v1/loadouts", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_with_loadouts(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        await _create_library_entry(async_client, auth_headers, seed_platforms)
        await _create_loadout(async_client, auth_headers)

        resp = await async_client.get("/v1/loadouts", headers=auth_headers)
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
        loadout = await _create_loadout(async_client, auth_headers)

        resp = await async_client.get("/v1/loadouts/latest", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["public_id"] == loadout["public_id"]

    async def test_latest_none_when_all_actioned(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        await _create_library_entry(async_client, auth_headers, seed_platforms)
        loadout = await _create_loadout(async_client, auth_headers)

        # Reject it.
        await async_client.post(
            f"/v1/loadouts/{loadout['public_id']}/reject",
            headers=auth_headers,
        )

        resp = await async_client.get("/v1/loadouts/latest", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() is None
