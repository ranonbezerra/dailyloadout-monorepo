"""Comprehensive tests for the library endpoints (v1/games, v1/platforms, v1/library)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient

# =====================================================================
# Helpers
# =====================================================================


def _game_payload(
    slug: str = "elden-ring",
    title: str = "Elden Ring",
    **overrides: Any,
) -> dict[str, Any]:
    """Return a default game creation payload, with optional overrides."""
    payload: dict[str, Any] = {
        "slug": slug,
        "title": title,
        "metadata_source": "manual",
        "summary": "An action RPG by FromSoftware.",
        "genres": ["action", "rpg"],
    }
    payload.update(overrides)
    return payload


# =====================================================================
# Fixtures
# =====================================================================


@pytest.fixture
async def create_game(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    seed_platforms: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create a game via the API and return the parsed response body."""
    resp = await async_client.post(
        "/v1/games",
        json=_game_payload(),
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture
async def library_entry(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    create_game: dict[str, Any],
    seed_platforms: list[dict[str, Any]],
) -> dict[str, Any]:
    """Add a game to the library and return the parsed response body."""
    resp = await async_client.post(
        "/v1/library",
        json={
            "game_public_id": create_game["public_id"],
            "platform_id": seed_platforms[0]["id"],
            "status": "backlog",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# =====================================================================
# Platforms
# =====================================================================


class TestPlatforms:
    """GET /v1/platforms"""

    async def test_list_platforms(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        resp = await async_client.get("/v1/platforms", headers=auth_headers)
        assert resp.status_code == 200

        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 10

        # Each platform must have the expected shape.
        first = data[0]
        assert "id" in first
        assert "slug" in first
        assert "label" in first
        assert "family" in first

    async def test_list_platforms_unauthorized(
        self,
        async_client: AsyncClient,
    ) -> None:
        resp = await async_client.get("/v1/platforms")
        assert resp.status_code == 401


# =====================================================================
# Create Game
# =====================================================================


class TestCreateGame:
    """POST /v1/games"""

    async def test_create_game_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        payload = _game_payload()
        resp = await async_client.post("/v1/games", json=payload, headers=auth_headers)
        assert resp.status_code == 201

        data = resp.json()
        assert data["slug"] == "elden-ring"
        assert data["title"] == "Elden Ring"
        assert data["metadata_source"] == "manual"
        assert data["genres"] == ["action", "rpg"]
        assert "public_id" in data
        assert "created_at" in data

    async def test_create_game_duplicate_slug(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        payload = _game_payload(slug="hollow-knight", title="Hollow Knight")
        resp1 = await async_client.post("/v1/games", json=payload, headers=auth_headers)
        assert resp1.status_code == 201

        resp2 = await async_client.post("/v1/games", json=payload, headers=auth_headers)
        assert resp2.status_code == 409

    async def test_create_game_unauthorized(
        self,
        async_client: AsyncClient,
    ) -> None:
        payload = _game_payload()
        resp = await async_client.post("/v1/games", json=payload)
        assert resp.status_code == 401


# =====================================================================
# Search Games
# =====================================================================


class TestSearchGames:
    """GET /v1/games/search"""

    async def test_search_games_by_title(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        create_game: dict[str, Any],
    ) -> None:
        resp = await async_client.get(
            "/v1/games/search",
            params={"q": "Elden"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["slug"] == "elden-ring"

    async def test_search_games_empty_query(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        # The endpoint requires min_length=1 on `q`, so an empty string
        # should be rejected with 422.
        resp = await async_client.get(
            "/v1/games/search",
            params={"q": ""},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_search_games_no_results(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        resp = await async_client.get(
            "/v1/games/search",
            params={"q": "zzz_nonexistent_game_zzz"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

        data = resp.json()
        assert data == []


# =====================================================================
# Add to Library
# =====================================================================


class TestAddToLibrary:
    """POST /v1/library"""

    async def test_add_to_library_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        create_game: dict[str, Any],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        resp = await async_client.post(
            "/v1/library",
            json={
                "game_public_id": create_game["public_id"],
                "platform_id": seed_platforms[0]["id"],
                "status": "playing",
                "notes": "First playthrough",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201

        data = resp.json()
        assert "public_id" in data
        assert data["status"] == "playing"
        assert data["notes"] == "First playthrough"
        assert data["game"]["slug"] == "elden-ring"
        assert data["platform"]["id"] == seed_platforms[0]["id"]

    async def test_add_to_library_duplicate(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        create_game: dict[str, Any],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        body = {
            "game_public_id": create_game["public_id"],
            "platform_id": seed_platforms[0]["id"],
        }
        resp1 = await async_client.post("/v1/library", json=body, headers=auth_headers)
        assert resp1.status_code == 201

        resp2 = await async_client.post("/v1/library", json=body, headers=auth_headers)
        assert resp2.status_code == 409

    async def test_add_to_library_game_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        resp = await async_client.post(
            "/v1/library",
            json={
                "game_public_id": str(uuid4()),
                "platform_id": seed_platforms[0]["id"],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_add_to_library_platform_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        create_game: dict[str, Any],
    ) -> None:
        resp = await async_client.post(
            "/v1/library",
            json={
                "game_public_id": create_game["public_id"],
                "platform_id": 99999,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404


# =====================================================================
# List Library
# =====================================================================


class TestListLibrary:
    """GET /v1/library"""

    async def test_list_library_empty(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        resp = await async_client.get("/v1/library", headers=auth_headers)
        assert resp.status_code == 200

        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_library_with_entries(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        library_entry: dict[str, Any],
    ) -> None:
        resp = await async_client.get("/v1/library", headers=auth_headers)
        assert resp.status_code == 200

        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

        item = data["items"][0]
        assert item["public_id"] == library_entry["public_id"]
        assert "game" in item
        assert "platform" in item
        assert item["game"]["slug"] == "elden-ring"

    async def test_list_library_filter_by_status(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        create_game: dict[str, Any],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        # Add two entries with different statuses via different platforms.
        await async_client.post(
            "/v1/library",
            json={
                "game_public_id": create_game["public_id"],
                "platform_id": seed_platforms[0]["id"],
                "status": "playing",
            },
            headers=auth_headers,
        )
        # Create a second game for the second entry.
        resp_g2 = await async_client.post(
            "/v1/games",
            json=_game_payload(slug="celeste", title="Celeste"),
            headers=auth_headers,
        )
        assert resp_g2.status_code == 201
        game2 = resp_g2.json()

        await async_client.post(
            "/v1/library",
            json={
                "game_public_id": game2["public_id"],
                "platform_id": seed_platforms[0]["id"],
                "status": "completed",
            },
            headers=auth_headers,
        )

        # Filter by "playing"
        resp = await async_client.get(
            "/v1/library",
            params={"status": "playing"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "playing"

    async def test_list_library_pagination(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        seed_platforms: list[dict[str, Any]],
    ) -> None:
        # Create 3 games and add them all to the library.
        slugs = ["game-a", "game-b", "game-c"]
        for slug in slugs:
            resp_g = await async_client.post(
                "/v1/games",
                json=_game_payload(slug=slug, title=slug.replace("-", " ").title()),
                headers=auth_headers,
            )
            assert resp_g.status_code == 201
            game = resp_g.json()
            resp_l = await async_client.post(
                "/v1/library",
                json={
                    "game_public_id": game["public_id"],
                    "platform_id": seed_platforms[0]["id"],
                },
                headers=auth_headers,
            )
            assert resp_l.status_code == 201

        # Total should be 3.
        resp_all = await async_client.get(
            "/v1/library",
            params={"limit": 100, "offset": 0},
            headers=auth_headers,
        )
        assert resp_all.json()["total"] == 3

        # Limit 2 offset 0 => 2 items, total still 3.
        resp_page1 = await async_client.get(
            "/v1/library",
            params={"limit": 2, "offset": 0},
            headers=auth_headers,
        )
        page1 = resp_page1.json()
        assert len(page1["items"]) == 2
        assert page1["total"] == 3

        # Limit 2 offset 2 => 1 item.
        resp_page2 = await async_client.get(
            "/v1/library",
            params={"limit": 2, "offset": 2},
            headers=auth_headers,
        )
        page2 = resp_page2.json()
        assert len(page2["items"]) == 1
        assert page2["total"] == 3


# =====================================================================
# Update Library Entry
# =====================================================================


class TestUpdateLibraryEntry:
    """PATCH /v1/library/{public_id}"""

    async def test_update_entry_status(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        library_entry: dict[str, Any],
    ) -> None:
        public_id = library_entry["public_id"]
        resp = await async_client.patch(
            f"/v1/library/{public_id}",
            json={"status": "playing"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

        data = resp.json()
        assert data["status"] == "playing"
        assert data["public_id"] == public_id

    async def test_update_entry_notes(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        library_entry: dict[str, Any],
    ) -> None:
        public_id = library_entry["public_id"]
        resp = await async_client.patch(
            f"/v1/library/{public_id}",
            json={"notes": "Updated notes"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

        data = resp.json()
        assert data["notes"] == "Updated notes"

    async def test_update_entry_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        fake_id = str(uuid4())
        resp = await async_client.patch(
            f"/v1/library/{fake_id}",
            json={"status": "completed"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_update_entry_other_user(
        self,
        async_client: AsyncClient,
        library_entry: dict[str, Any],
    ) -> None:
        """A different user should not be able to update another user's entry."""
        # Register a second user.
        resp_reg = await async_client.post(
            "/v1/auth/register",
            json={
                "email": "other@example.com",
                "password": "StrongPass123",
                "display_name": "Other Player",
            },
        )
        assert resp_reg.status_code == 201
        other_headers = {"Authorization": f"Bearer {resp_reg.json()['access_token']}"}

        public_id = library_entry["public_id"]
        resp = await async_client.patch(
            f"/v1/library/{public_id}",
            json={"status": "completed"},
            headers=other_headers,
        )
        assert resp.status_code == 404


# =====================================================================
# Delete Library Entry
# =====================================================================


class TestDeleteLibraryEntry:
    """DELETE /v1/library/{public_id}"""

    async def test_delete_entry_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        library_entry: dict[str, Any],
    ) -> None:
        public_id = library_entry["public_id"]
        resp = await async_client.delete(
            f"/v1/library/{public_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 204

        # Verify the entry is gone.
        resp_list = await async_client.get("/v1/library", headers=auth_headers)
        assert resp_list.json()["total"] == 0

    async def test_delete_entry_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        fake_id = str(uuid4())
        resp = await async_client.delete(
            f"/v1/library/{fake_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_delete_entry_idempotent(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        library_entry: dict[str, Any],
    ) -> None:
        """Deleting the same entry a second time should return 404."""
        public_id = library_entry["public_id"]

        resp1 = await async_client.delete(
            f"/v1/library/{public_id}",
            headers=auth_headers,
        )
        assert resp1.status_code == 204

        resp2 = await async_client.delete(
            f"/v1/library/{public_id}",
            headers=auth_headers,
        )
        assert resp2.status_code == 404
