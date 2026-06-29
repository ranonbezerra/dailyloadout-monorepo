"""Tests for manual game creation: IGDB reconcile + per-user scoping.

Covers the two behaviours added to ``POST /v1/games``:

1. **Reconcile** — when an IGDB client is configured and confidently matches the
   submitted title, the server stores/reuses a canonical GLOBAL ``igdb`` row.
2. **Per-user manual** — without a match (default in tests), a manual row is
   scoped to its creator; two users may share a slug, the same user may not.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Any

import pytest
from httpx import AsyncClient

from slate.infrastructure.igdb.schemas import IGDBGame


class FakeIGDBClient:
    """An ``IGDBSearchClient`` returning canned results keyed by query title."""

    def __init__(self, catalogue: dict[str, list[IGDBGame]]) -> None:
        self._catalogue = catalogue
        self.calls: list[str] = []

    async def search_games(self, query: str, limit: int = 5) -> list[IGDBGame]:
        self.calls.append(query)
        return self._catalogue.get(query, [])[:limit]


def _payload(slug: str, title: str, **overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"slug": slug, "title": title}
    body.update(overrides)
    return body


async def _register(client: AsyncClient, email: str) -> dict[str, str]:
    resp = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": "StrongPass123", "display_name": "P"},
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def use_igdb() -> Callable[[FakeIGDBClient], None]:
    """Override the IGDB client dependency with a fake; cleaned up after the test."""
    from slate.deps.capture import get_igdb_client_dep
    from slate.main import app

    def _apply(fake: FakeIGDBClient) -> None:
        app.dependency_overrides[get_igdb_client_dep] = lambda: fake

    return _apply


@pytest.fixture(autouse=True)
async def _restore_igdb() -> AsyncIterator[None]:
    """Restore the default ``None`` IGDB override after each test."""
    yield
    from slate.deps.capture import get_igdb_client_dep
    from slate.main import app

    app.dependency_overrides[get_igdb_client_dep] = lambda: None


# =====================================================================
# Reconcile against IGDB
# =====================================================================


class TestReconcile:
    async def test_confident_match_creates_igdb_row(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        use_igdb: Callable[[FakeIGDBClient], None],
    ) -> None:
        use_igdb(
            FakeIGDBClient(
                {
                    "Hades": [
                        IGDBGame(
                            igdb_id=100,
                            title="Hades",
                            genres=["action", "roguelike"],
                            summary="A rogue-like dungeon crawler.",
                        )
                    ]
                }
            )
        )
        resp = await async_client.post(
            "/v1/games",
            json=_payload("hades-manual", "Hades"),
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        # Server overrode the manual intent with the canonical IGDB row.
        assert data["metadata_source"] == "igdb"
        assert data["igdb_id"] == 100
        assert data["genres"] == ["action", "roguelike"]
        # The canonical slug comes from the IGDB title, not the client's slug.
        assert data["slug"] == "hades"

    async def test_second_user_reuses_global_row(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        use_igdb: Callable[[FakeIGDBClient], None],
    ) -> None:
        catalogue = {"Hades": [IGDBGame(igdb_id=100, title="Hades")]}
        use_igdb(FakeIGDBClient(catalogue))

        first = await async_client.post(
            "/v1/games", json=_payload("hades-a", "Hades"), headers=auth_headers
        )
        assert first.status_code == 201

        other = await _register(async_client, "second@example.com")
        use_igdb(FakeIGDBClient(catalogue))
        second = await async_client.post(
            "/v1/games", json=_payload("hades-b", "Hades"), headers=other
        )
        assert second.status_code == 201
        # Same canonical row reused — identical public_id, no duplicate.
        assert second.json()["public_id"] == first.json()["public_id"]
        assert second.json()["igdb_id"] == 100

    async def test_no_confident_match_falls_through_to_manual(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        use_igdb: Callable[[FakeIGDBClient], None],
    ) -> None:
        # Candidate title is wildly different -> below the fuzzy threshold.
        use_igdb(
            FakeIGDBClient({"Obscure Indie": [IGDBGame(igdb_id=7, title="Totally Unrelated")]})
        )
        resp = await async_client.post(
            "/v1/games",
            json=_payload("obscure-indie", "Obscure Indie"),
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["metadata_source"] == "manual"
        assert resp.json()["igdb_id"] is None


# =====================================================================
# DB-first: enrich an existing un-enriched GLOBAL row on the fly
# =====================================================================


async def _seed_global_unenriched(slug: str, title: str) -> str:
    """Insert a GLOBAL (created_by_user_id=None) row lacking IGDB info."""
    from slate.infrastructure.db.repositories.game import GameRepository
    from tests.conftest import _TestSessionFactory

    async with _TestSessionFactory() as session:
        game = await GameRepository(session).create(
            slug=slug,
            title=title,
            metadata_source="capture",
            igdb_id=None,
            created_by_user_id=None,
        )
        await session.commit()
        return str(game.public_id)


class TestOnTheFlyEnrichment:
    async def test_existing_global_row_enriched_in_place(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        use_igdb: Callable[[FakeIGDBClient], None],
    ) -> None:
        # A global row exists for this slug but has no IGDB metadata yet.
        public_id = await _seed_global_unenriched("celeste", "Celeste")
        use_igdb(
            FakeIGDBClient(
                {
                    "Celeste": [
                        IGDBGame(
                            igdb_id=200,
                            title="Celeste",
                            genres=["platformer"],
                            cover_url="https://img/celeste.jpg",
                            summary="A mountain to climb.",
                        )
                    ]
                }
            )
        )
        resp = await async_client.post(
            "/v1/games", json=_payload("celeste", "Celeste"), headers=auth_headers
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        # Same row, now enriched in place.
        assert data["public_id"] == public_id
        assert data["igdb_id"] == 200
        assert data["genres"] == ["platformer"]
        assert data["metadata_source"] == "igdb"

    async def test_existing_enriched_row_left_untouched(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        use_igdb: Callable[[FakeIGDBClient], None],
    ) -> None:
        # An already-IGDB row must not be re-enriched / IGDB not even consulted.
        from slate.infrastructure.db.repositories.game import GameRepository
        from tests.conftest import _TestSessionFactory

        async with _TestSessionFactory() as session:
            game = await GameRepository(session).create(
                slug="enriched",
                title="Enriched",
                metadata_source="igdb",
                igdb_id=300,
                genres=["rpg"],
            )
            await session.commit()
            public_id = str(game.public_id)

        fake = FakeIGDBClient({"Enriched": [IGDBGame(igdb_id=999, title="Wrong")]})
        use_igdb(fake)
        resp = await async_client.post(
            "/v1/games", json=_payload("enriched", "Enriched"), headers=auth_headers
        )
        assert resp.status_code == 201
        assert resp.json()["public_id"] == public_id
        assert resp.json()["igdb_id"] == 300
        # IGDB was never queried — the row already had its data.
        assert fake.calls == []

    async def test_collision_leaves_row_unenriched(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        use_igdb: Callable[[FakeIGDBClient], None],
    ) -> None:
        # The matched igdb_id already belongs to a *different* canonical row, so
        # the un-enriched row is left as-is (collision-skip semantics).
        from slate.infrastructure.db.repositories.game import GameRepository
        from tests.conftest import _TestSessionFactory

        async with _TestSessionFactory() as session:
            repo = GameRepository(session)
            await repo.create(
                slug="hades-canonical",
                title="Hades (Canonical)",
                metadata_source="igdb",
                igdb_id=400,
            )
            dup = await repo.create(
                slug="hades-dup",
                title="Hades",
                metadata_source="capture",
                igdb_id=None,
            )
            await session.commit()
            dup_public_id = str(dup.public_id)

        use_igdb(FakeIGDBClient({"Hades": [IGDBGame(igdb_id=400, title="Hades")]}))
        resp = await async_client.post(
            "/v1/games", json=_payload("hades-dup", "Hades"), headers=auth_headers
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["public_id"] == dup_public_id
        assert data["igdb_id"] is None  # left untouched
        assert data["metadata_source"] == "capture"


# =====================================================================
# Per-user manual games
# =====================================================================


class TestSharedManual:
    async def test_second_user_relates_to_same_manual_row(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        # IGDB client is None by default -> manual path. ``get_by_slug`` is a
        # GLOBAL lookup, so a second user creating the same slug dedups onto the
        # existing row (no duplicate) even though it is still private.
        first = await async_client.post(
            "/v1/games", json=_payload("my-game", "My Game"), headers=auth_headers
        )
        assert first.status_code == 201

        other = await _register(async_client, "second@example.com")
        second = await async_client.post(
            "/v1/games", json=_payload("my-game", "My Game"), headers=other
        )
        assert second.status_code == 201
        # Same underlying row reused — identical public_id, no dup.
        assert second.json()["public_id"] == first.json()["public_id"]

    async def test_same_user_same_slug_is_idempotent(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        body = _payload("dup-game", "Dup Game")
        first = await async_client.post("/v1/games", json=body, headers=auth_headers)
        assert first.status_code == 201

        # Re-posting returns the same manual row — no conflict.
        second = await async_client.post("/v1/games", json=body, headers=auth_headers)
        assert second.status_code == 201
        assert second.json()["public_id"] == first.json()["public_id"]


# =====================================================================
# Shared visibility (search)
# =====================================================================


class TestSharedVisibility:
    async def test_private_manual_game_hidden_from_other_user(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        # User A adds a manual game; it is born PRIVATE (anti-abuse Block C).
        await async_client.post(
            "/v1/games",
            json=_payload("indie-gem", "Indie Gem"),
            headers=auth_headers,
        )

        # The creator still sees their own private row...
        creator_search = await async_client.get(
            "/v1/games/search", params={"q": "Indie"}, headers=auth_headers
        )
        assert creator_search.status_code == 200
        assert any(g["slug"] == "indie-gem" for g in creator_search.json())

        # ...but user B must NOT discover an unvalidated private manual row.
        other = await _register(async_client, "second@example.com")
        other_search = await async_client.get(
            "/v1/games/search", params={"q": "Indie"}, headers=other
        )
        assert other_search.status_code == 200
        assert not any(g["slug"] == "indie-gem" for g in other_search.json())

    async def test_igdb_row_visible_to_everyone(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        use_igdb: Callable[[FakeIGDBClient], None],
    ) -> None:
        use_igdb(
            FakeIGDBClient({"Stardew Valley": [IGDBGame(igdb_id=55, title="Stardew Valley")]})
        )
        created = await async_client.post(
            "/v1/games",
            json=_payload("stardew", "Stardew Valley"),
            headers=auth_headers,
        )
        assert created.status_code == 201
        assert created.json()["metadata_source"] == "igdb"

        other = await _register(async_client, "second@example.com")
        search = await async_client.get("/v1/games/search", params={"q": "Stardew"}, headers=other)
        assert search.status_code == 200
        assert any(g["slug"] == "stardew-valley" for g in search.json())

    async def test_igdb_enrichment_makes_private_row_visible(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        use_igdb: Callable[[FakeIGDBClient], None],
    ) -> None:
        """On-the-fly IGDB enrichment of a private manual row makes it global."""
        # User A creates a private manual row (no IGDB client configured).
        created = await async_client.post(
            "/v1/games", json=_payload("celeste", "Celeste"), headers=auth_headers
        )
        assert created.status_code == 201
        assert created.json()["igdb_id"] is None

        other = await _register(async_client, "second@example.com")
        hidden = await async_client.get("/v1/games/search", params={"q": "Celeste"}, headers=other)
        assert not any(g["slug"] == "celeste" for g in hidden.json())

        # User B re-resolves the same slug with IGDB available: the existing
        # private row is enriched in place (igdb_id set), which makes it visible.
        use_igdb(FakeIGDBClient({"Celeste": [IGDBGame(igdb_id=200, title="Celeste")]}))
        enriched = await async_client.post(
            "/v1/games", json=_payload("celeste", "Celeste"), headers=other
        )
        assert enriched.status_code == 201
        assert enriched.json()["igdb_id"] == 200

        now_visible = await async_client.get(
            "/v1/games/search", params={"q": "Celeste"}, headers=other
        )
        assert any(g["slug"] == "celeste" for g in now_visible.json())


class TestGenresVisibility:
    """GET /v1/games/genres respects per-user catalogue visibility."""

    async def test_private_manual_genres_hidden_from_other_user(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        await async_client.post(
            "/v1/games",
            json=_payload("metroidvania-x", "Metroidvania X", genres=["metroidvania"]),
            headers=auth_headers,
        )

        # Creator sees the genre from their own private row.
        own = await async_client.get("/v1/games/genres", headers=auth_headers)
        assert own.status_code == 200
        assert "metroidvania" in own.json()

        # A different user must not see genres sourced from a private manual row.
        other = await _register(async_client, "second@example.com")
        other_genres = await async_client.get("/v1/games/genres", headers=other)
        assert other_genres.status_code == 200
        assert "metroidvania" not in other_genres.json()


class TestDistinctOwnerPromotion:
    """A private manual row is promoted to shared once enough users own it."""

    async def _seed_platform(self) -> int:
        from slate.infrastructure.db.models import Platform
        from tests.conftest import _TestSessionFactory

        async with _TestSessionFactory() as session:
            platform = Platform(slug="pc", label="PC", family="pc")
            session.add(platform)
            await session.flush()
            platform_id = platform.id
            await session.commit()
        return platform_id

    async def test_fifth_distinct_owner_flips_to_shared(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        platform_id = await self._seed_platform()

        # User A (creator) makes the private manual row and adds it (owner #1).
        created = await async_client.post(
            "/v1/games", json=_payload("backlog-buddy", "Backlog Buddy"), headers=auth_headers
        )
        assert created.status_code == 201
        game_public_id = created.json()["public_id"]
        add_a = await async_client.post(
            "/v1/library",
            json={"game_public_id": game_public_id, "platform_ids": [platform_id]},
            headers=auth_headers,
        )
        assert add_a.status_code == 201

        # Owners #2..#4 add it. With threshold 5 it stays private throughout.
        for i in range(2, 5):
            hdr = await _register(async_client, f"owner{i}@example.com")
            resolved = await async_client.post(
                "/v1/games", json=_payload("backlog-buddy", "Backlog Buddy"), headers=hdr
            )
            assert resolved.json()["public_id"] == game_public_id
            await async_client.post(
                "/v1/library",
                json={"game_public_id": game_public_id, "platform_ids": [platform_id]},
                headers=hdr,
            )
            search = await async_client.get(
                "/v1/games/search", params={"q": "Backlog"}, headers=hdr
            )
            # Each owner sees it only via /games (their own resolve), but search
            # still excludes it because it is private and they are not the creator.
            assert not any(g["slug"] == "backlog-buddy" for g in search.json())

        # The 5th DISTINCT owner crosses the threshold -> promoted to shared.
        fifth = await _register(async_client, "owner5@example.com")
        await async_client.post(
            "/v1/games", json=_payload("backlog-buddy", "Backlog Buddy"), headers=fifth
        )
        promote = await async_client.post(
            "/v1/library",
            json={"game_public_id": game_public_id, "platform_ids": [platform_id]},
            headers=fifth,
        )
        assert promote.status_code == 201

        # Now a brand-new, non-owning user can discover it.
        outsider = await _register(async_client, "outsider@example.com")
        search = await async_client.get(
            "/v1/games/search", params={"q": "Backlog"}, headers=outsider
        )
        assert any(g["slug"] == "backlog-buddy" for g in search.json())

    async def test_same_user_multiple_platforms_does_not_promote(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Distinct OWNERS, not entries: one user on many platforms stays private."""
        from slate.infrastructure.db.models import Platform
        from tests.conftest import _TestSessionFactory

        async with _TestSessionFactory() as session:
            ids: list[int] = []
            for slug, label in [("pc", "PC"), ("ps5", "PS5"), ("switch", "Switch")]:
                plat = Platform(slug=slug, label=label, family=slug)
                session.add(plat)
                await session.flush()
                ids.append(plat.id)
            await session.commit()

        created = await async_client.post(
            "/v1/games", json=_payload("solo-spam", "Solo Spam"), headers=auth_headers
        )
        game_public_id = created.json()["public_id"]
        # One user, three platform entries — still one distinct owner.
        await async_client.post(
            "/v1/library",
            json={"game_public_id": game_public_id, "platform_ids": ids},
            headers=auth_headers,
        )

        other = await _register(async_client, "second@example.com")
        search = await async_client.get("/v1/games/search", params={"q": "Solo"}, headers=other)
        assert not any(g["slug"] == "solo-spam" for g in search.json())
