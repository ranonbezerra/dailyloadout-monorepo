"""Tests for the capture endpoints (v1/captures)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from httpx import AsyncClient

# =====================================================================
# Helpers
# =====================================================================


async def _submit_capture(
    client: AsyncClient,
    headers: dict[str, str],
    raw_text: str = "I just got Hollow Knight and Hades for the Switch",
) -> dict[str, Any]:
    """Submit a text capture and return the parsed response body."""
    resp = await client.post(
        "/v1/captures/text",
        json={"raw_text": raw_text},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# =====================================================================
# Test: Submit text capture
# =====================================================================


class TestSubmitTextCapture:
    async def test_submit_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        data = await _submit_capture(async_client, auth_headers)

        assert data["input_type"] == "text"
        assert data["raw_text"] == "I just got Hollow Knight and Hades for the Switch"
        assert data["status"] == "review"
        assert len(data["candidates"]) == 2

        titles = {c["title"] for c in data["candidates"]}
        assert "Hollow Knight" in titles
        assert "Hades" in titles

        for candidate in data["candidates"]:
            assert candidate["status"] == "pending"
            assert candidate["confidence"] is not None

    async def test_submit_single_game(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        data = await _submit_capture(async_client, auth_headers, "I bought Elden Ring today")

        assert data["status"] == "review"
        assert len(data["candidates"]) == 1
        assert data["candidates"][0]["title"] == "Elden Ring"

    async def test_submit_unknown_game(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """DummyLLMClient always returns at least one result for non-empty text."""
        data = await _submit_capture(async_client, auth_headers, "some random game text")

        assert data["status"] == "review"
        assert len(data["candidates"]) >= 1

    async def test_submit_too_short(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await async_client.post(
            "/v1/captures/text",
            json={"raw_text": "ab"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_submit_unauthorized(
        self,
        async_client: AsyncClient,
    ) -> None:
        resp = await async_client.post(
            "/v1/captures/text",
            json={"raw_text": "I got Hollow Knight"},
        )
        assert resp.status_code == 401


# =====================================================================
# Test: List captures
# =====================================================================


class TestListCaptures:
    async def test_list_empty(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await async_client.get("/v1/captures", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_with_captures(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        await _submit_capture(async_client, auth_headers, "got Hades")
        await _submit_capture(async_client, auth_headers, "got Celeste")

        resp = await async_client.get("/v1/captures", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_list_filter_by_status(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        await _submit_capture(async_client, auth_headers, "got Hades")

        resp = await async_client.get(
            "/v1/captures", params={"status": "review"}, headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

        resp = await async_client.get(
            "/v1/captures", params={"status": "queued"}, headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    async def test_list_pagination(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        await _submit_capture(async_client, auth_headers, "got Hades")
        await _submit_capture(async_client, auth_headers, "got Celeste")
        await _submit_capture(async_client, auth_headers, "got Elden Ring")

        resp = await async_client.get("/v1/captures", params={"limit": 2}, headers=auth_headers)
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 3


# =====================================================================
# Test: Get single capture
# =====================================================================


class TestGetCapture:
    async def test_get_capture(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        capture = await _submit_capture(async_client, auth_headers)

        resp = await async_client.get(f"/v1/captures/{capture['public_id']}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["public_id"] == capture["public_id"]
        assert len(data["candidates"]) == len(capture["candidates"])

    async def test_get_capture_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await async_client.get(f"/v1/captures/{uuid4()}", headers=auth_headers)
        assert resp.status_code == 404


# =====================================================================
# Test: Confirm candidate
# =====================================================================


class TestConfirmCandidate:
    async def test_confirm_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        capture = await _submit_capture(async_client, auth_headers, "I bought Hollow Knight")
        candidate = capture["candidates"][0]
        platform_id = seed_platforms[0]["id"]

        resp = await async_client.post(
            f"/v1/captures/{capture['public_id']}/candidates/{candidate['public_id']}/confirm",
            json={"platform_id": platform_id, "status": "backlog"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        entry = resp.json()
        assert entry["status"] == "backlog"
        assert entry["game"]["title"] == "Hollow Knight"

    async def test_confirm_creates_game(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Confirming a candidate should create a game in the catalog."""
        capture = await _submit_capture(async_client, auth_headers, "I bought Hades")
        candidate = capture["candidates"][0]
        platform_id = seed_platforms[0]["id"]

        await async_client.post(
            f"/v1/captures/{capture['public_id']}/candidates/{candidate['public_id']}/confirm",
            json={"platform_id": platform_id},
            headers=auth_headers,
        )

        # Verify the game is now searchable.
        resp = await async_client.get(
            "/v1/games/search", params={"q": "Hades"}, headers=auth_headers
        )
        assert resp.status_code == 200
        games = resp.json()
        assert any(g["title"] == "Hades" for g in games)

    async def test_confirm_updates_capture_status(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """When all candidates are confirmed, capture status becomes 'committed'."""
        capture = await _submit_capture(async_client, auth_headers, "I bought Hades")
        candidate = capture["candidates"][0]
        platform_id = seed_platforms[0]["id"]

        await async_client.post(
            f"/v1/captures/{capture['public_id']}/candidates/{candidate['public_id']}/confirm",
            json={"platform_id": platform_id},
            headers=auth_headers,
        )

        resp = await async_client.get(f"/v1/captures/{capture['public_id']}", headers=auth_headers)
        assert resp.json()["status"] == "committed"

    async def test_confirm_already_confirmed(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        capture = await _submit_capture(async_client, auth_headers, "I bought Hades")
        candidate = capture["candidates"][0]
        platform_id = seed_platforms[0]["id"]

        await async_client.post(
            f"/v1/captures/{capture['public_id']}/candidates/{candidate['public_id']}/confirm",
            json={"platform_id": platform_id},
            headers=auth_headers,
        )

        # Try confirming again.
        resp = await async_client.post(
            f"/v1/captures/{capture['public_id']}/candidates/{candidate['public_id']}/confirm",
            json={"platform_id": platform_id},
            headers=auth_headers,
        )
        assert resp.status_code == 409

    async def test_confirm_invalid_platform(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        capture = await _submit_capture(async_client, auth_headers, "I bought Hades")
        candidate = capture["candidates"][0]

        resp = await async_client.post(
            f"/v1/captures/{capture['public_id']}/candidates/{candidate['public_id']}/confirm",
            json={"platform_id": 9999},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_confirm_candidate_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        capture = await _submit_capture(async_client, auth_headers, "I bought Hades")

        resp = await async_client.post(
            f"/v1/captures/{capture['public_id']}/candidates/{uuid4()}/confirm",
            json={"platform_id": seed_platforms[0]["id"]},
            headers=auth_headers,
        )
        assert resp.status_code == 404


# =====================================================================
# Test: Reject candidate
# =====================================================================


class TestRejectCandidate:
    async def test_reject_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        capture = await _submit_capture(async_client, auth_headers, "I bought Hades")
        candidate = capture["candidates"][0]

        resp = await async_client.post(
            f"/v1/captures/{capture['public_id']}/candidates/{candidate['public_id']}/reject",
            headers=auth_headers,
        )
        assert resp.status_code == 204

    async def test_reject_updates_capture_status(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """When all candidates are rejected, capture status becomes 'cancelled'."""
        capture = await _submit_capture(async_client, auth_headers, "I bought Hades")
        candidate = capture["candidates"][0]

        await async_client.post(
            f"/v1/captures/{capture['public_id']}/candidates/{candidate['public_id']}/reject",
            headers=auth_headers,
        )

        resp = await async_client.get(f"/v1/captures/{capture['public_id']}", headers=auth_headers)
        assert resp.json()["status"] == "cancelled"

    async def test_reject_already_rejected(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        capture = await _submit_capture(async_client, auth_headers, "I bought Hades")
        candidate = capture["candidates"][0]

        await async_client.post(
            f"/v1/captures/{capture['public_id']}/candidates/{candidate['public_id']}/reject",
            headers=auth_headers,
        )

        resp = await async_client.post(
            f"/v1/captures/{capture['public_id']}/candidates/{candidate['public_id']}/reject",
            headers=auth_headers,
        )
        assert resp.status_code == 409


# =====================================================================
# Test: Mixed confirm/reject flow
# =====================================================================


class TestMixedCandidateFlow:
    async def test_partially_committed(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Confirm one, reject the other -> capture becomes 'partially_committed'."""
        capture = await _submit_capture(
            async_client,
            auth_headers,
            "I got Hollow Knight and Hades",
        )
        assert len(capture["candidates"]) == 2

        candidates = sorted(capture["candidates"], key=lambda c: c["title"])
        hades = candidates[0]  # Hades
        hk = candidates[1]  # Hollow Knight
        platform_id = seed_platforms[0]["id"]

        # Confirm Hades.
        resp = await async_client.post(
            f"/v1/captures/{capture['public_id']}/candidates/{hades['public_id']}/confirm",
            json={"platform_id": platform_id},
            headers=auth_headers,
        )
        assert resp.status_code == 200

        # Reject Hollow Knight.
        resp = await async_client.post(
            f"/v1/captures/{capture['public_id']}/candidates/{hk['public_id']}/reject",
            headers=auth_headers,
        )
        assert resp.status_code == 204

        # Capture should be partially_committed.
        resp = await async_client.get(f"/v1/captures/{capture['public_id']}", headers=auth_headers)
        assert resp.json()["status"] == "partially_committed"

    async def test_confirm_all(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Confirm all candidates -> capture becomes 'committed'."""
        capture = await _submit_capture(
            async_client,
            auth_headers,
            "I got Hollow Knight and Hades",
        )
        platform_id = seed_platforms[0]["id"]

        for candidate in capture["candidates"]:
            resp = await async_client.post(
                f"/v1/captures/{capture['public_id']}/candidates/{candidate['public_id']}/confirm",
                json={"platform_id": platform_id},
                headers=auth_headers,
            )
            assert resp.status_code == 200

        resp = await async_client.get(f"/v1/captures/{capture['public_id']}", headers=auth_headers)
        assert resp.json()["status"] == "committed"

    async def test_confirmed_game_appears_in_library(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        """Confirmed candidates should create library entries."""
        capture = await _submit_capture(async_client, auth_headers, "I bought Hades")
        candidate = capture["candidates"][0]
        platform_id = seed_platforms[0]["id"]

        await async_client.post(
            f"/v1/captures/{capture['public_id']}/candidates/{candidate['public_id']}/confirm",
            json={"platform_id": platform_id, "status": "playing"},
            headers=auth_headers,
        )

        # Verify game is in the library.
        resp = await async_client.get("/v1/library", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["game"]["title"] == "Hades"
        assert data["items"][0]["status"] == "playing"
