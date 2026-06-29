"""Stats endpoint tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient

from slate.infrastructure.db.models import Game, LibraryEntry, PlaySession
from tests.conftest import _TestSessionFactory


async def _create_test_data(platform_id: int) -> int:
    """Create a user's library entries and play_sessions, return user_id from the play_sessions."""
    async with _TestSessionFactory() as session:
        game = Game(
            slug="hollow-knight",
            title="Hollow Knight",
            metadata_source="user",
            genres=["metroidvania", "action"],
        )
        session.add(game)
        await session.flush()

        entry = LibraryEntry(
            user_id=1,  # Will be overridden in tests
            game_id=game.id,
            platform_id=platform_id,
            status="playing",
        )
        session.add(entry)
        await session.flush()

        now = datetime.now(UTC)
        for i in range(3):
            play_session = PlaySession(
                user_id=1,
                library_entry_id=entry.id,
                play_session_type="regular",
                started_at=now - timedelta(days=i, hours=2),
                ended_at=now - timedelta(days=i),
                ended_via="wrap_up_completed",
                wrap_up_text=f"Session {i} wrap_up",
            )
            session.add(play_session)

        await session.commit()
        return entry.user_id


class TestStatsOverview:
    async def test_overview_empty(self, async_client: AsyncClient, auth_headers: dict) -> None:
        resp = await async_client.get("/v1/stats/overview", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_games"] == 0
        assert data["status_counts"] == {}
        assert data["play_sessions_last_30d"] == 0
        assert data["avg_play_session_duration_minutes"] is None

    async def test_overview_with_data(
        self, async_client: AsyncClient, auth_headers: dict, seed_platforms: list[dict]
    ) -> None:
        # Create a library entry
        game_resp = await async_client.post(
            "/v1/games",
            json={"slug": "hk", "title": "Hollow Knight", "metadata_source": "user"},
            headers=auth_headers,
        )
        game_id = game_resp.json()["public_id"]

        lib_json = {
            "game_public_id": game_id,
            "platform_ids": [seed_platforms[0]["id"]],
            "status": "playing",
        }
        await async_client.post("/v1/library", json=lib_json, headers=auth_headers)

        resp = await async_client.get("/v1/stats/overview", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_games"] == 1
        assert data["status_counts"]["playing"] == 1

    async def test_overview_unauthorized(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/v1/stats/overview")
        assert resp.status_code == 401


class TestPlayHeatmap:
    async def test_heatmap_empty(self, async_client: AsyncClient, auth_headers: dict) -> None:
        resp = await async_client.get("/v1/stats/play-heatmap", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["days"] == []

    async def test_heatmap_with_play_sessions(
        self, async_client: AsyncClient, auth_headers: dict, seed_platforms: list[dict]
    ) -> None:
        # Create game + entry + start play_session + end play_session
        game_resp = await async_client.post(
            "/v1/games",
            json={"slug": "celeste", "title": "Celeste", "metadata_source": "user"},
            headers=auth_headers,
        )
        game_id = game_resp.json()["public_id"]
        lib_json = {
            "game_public_id": game_id,
            "platform_ids": [seed_platforms[0]["id"]],
            "status": "playing",
        }
        entry_resp = await async_client.post("/v1/library", json=lib_json, headers=auth_headers)
        entry_id = entry_resp.json()["platforms"][0]["public_id"]
        play_session_resp = await async_client.post(
            "/v1/play-sessions",
            json={"library_entry_public_id": entry_id},
            headers=auth_headers,
        )
        play_session_id = play_session_resp.json()["public_id"]
        await async_client.post(
            f"/v1/play-sessions/{play_session_id}/end",
            json={"ended_via": "paused_app"},
            headers=auth_headers,
        )

        resp = await async_client.get("/v1/stats/play-heatmap", headers=auth_headers)
        assert resp.status_code == 200
        days = resp.json()["days"]
        assert len(days) >= 1
        assert days[0]["count"] == 1


class TestGenreStats:
    async def test_genres_empty(self, async_client: AsyncClient, auth_headers: dict) -> None:
        resp = await async_client.get("/v1/stats/genres", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["genres"] == []


class TestPlatformStats:
    async def test_platforms_empty(self, async_client: AsyncClient, auth_headers: dict) -> None:
        resp = await async_client.get("/v1/stats/platforms", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["platforms"] == []

    async def test_platforms_with_entries(
        self, async_client: AsyncClient, auth_headers: dict, seed_platforms: list[dict]
    ) -> None:
        game_resp = await async_client.post(
            "/v1/games",
            json={"slug": "hades", "title": "Hades", "metadata_source": "user"},
            headers=auth_headers,
        )
        game_id = game_resp.json()["public_id"]
        lib_json = {
            "game_public_id": game_id,
            "platform_ids": [seed_platforms[0]["id"]],
            "status": "backlog",
        }
        await async_client.post("/v1/library", json=lib_json, headers=auth_headers)

        resp = await async_client.get("/v1/stats/platforms", headers=auth_headers)
        assert resp.status_code == 200
        platforms = resp.json()["platforms"]
        assert len(platforms) == 1
        assert platforms[0]["game_count"] == 1


class TestTimeline:
    async def test_timeline_empty(self, async_client: AsyncClient, auth_headers: dict) -> None:
        resp = await async_client.get("/v1/stats/timeline", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_timeline_with_play_sessions(
        self, async_client: AsyncClient, auth_headers: dict, seed_platforms: list[dict]
    ) -> None:
        game_resp = await async_client.post(
            "/v1/games",
            json={"slug": "ori", "title": "Ori", "metadata_source": "user"},
            headers=auth_headers,
        )
        game_id = game_resp.json()["public_id"]
        lib_json = {
            "game_public_id": game_id,
            "platform_ids": [seed_platforms[0]["id"]],
            "status": "playing",
        }
        entry_resp = await async_client.post("/v1/library", json=lib_json, headers=auth_headers)
        entry_id = entry_resp.json()["platforms"][0]["public_id"]
        play_session_resp = await async_client.post(
            "/v1/play-sessions",
            json={"library_entry_public_id": entry_id},
            headers=auth_headers,
        )
        play_session_id = play_session_resp.json()["public_id"]
        await async_client.post(
            f"/v1/play-sessions/{play_session_id}/end",
            json={"ended_via": "paused_app"},
            headers=auth_headers,
        )

        resp = await async_client.get("/v1/stats/timeline", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["game_title"] == "Ori"

    async def test_timeline_pagination(
        self, async_client: AsyncClient, auth_headers: dict
    ) -> None:
        resp = await async_client.get("/v1/stats/timeline?limit=5&offset=0", headers=auth_headers)
        assert resp.status_code == 200
