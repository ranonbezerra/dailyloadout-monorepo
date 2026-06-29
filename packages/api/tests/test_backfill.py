"""Tests for the IGDB backfill (core/library/backfill.py + repo.list_unenriched)."""

from __future__ import annotations

from datetime import date

from slate.core.library.backfill import backfill_games, enrich_game
from slate.infrastructure.db.repositories.game import GameRepository
from slate.infrastructure.igdb.schemas import IGDBGame
from tests.conftest import _TestSessionFactory


class FakeIGDBClient:
    """An ``IGDBSearchClient`` returning canned results keyed by query title."""

    def __init__(self, catalogue: dict[str, list[IGDBGame]]) -> None:
        self._catalogue = catalogue
        self.calls: list[str] = []

    async def search_games(self, query: str, limit: int = 5) -> list[IGDBGame]:
        self.calls.append(query)
        return self._catalogue.get(query, [])[:limit]


async def _make_game(repo: GameRepository, *, title: str, igdb_id: int | None = None) -> int:
    game = await repo.create(
        slug=title.lower().replace(" ", "-"),
        title=title,
        metadata_source="igdb" if igdb_id else "capture",
        igdb_id=igdb_id,
    )
    return game.id


class TestListUnenriched:
    async def test_returns_only_games_without_igdb_id(self) -> None:
        async with _TestSessionFactory() as session:
            repo = GameRepository(session)
            await _make_game(repo, title="Old Capture Game")
            await _make_game(repo, title="Already Enriched", igdb_id=42)
            await session.flush()

            unenriched = await repo.list_unenriched()

        titles = [g.title for g in unenriched]
        assert titles == ["Old Capture Game"]

    async def test_respects_limit(self) -> None:
        async with _TestSessionFactory() as session:
            repo = GameRepository(session)
            for i in range(3):
                await _make_game(repo, title=f"Game {i}")
            await session.flush()

            assert len(await repo.list_unenriched(limit=2)) == 2


class TestBackfillGames:
    async def test_enriches_matching_game(self) -> None:
        async with _TestSessionFactory() as session:
            repo = GameRepository(session)
            game_id = await _make_game(repo, title="Hollow Knight")
            await session.flush()

            client = FakeIGDBClient(
                {
                    "Hollow Knight": [
                        IGDBGame(
                            igdb_id=1,
                            title="Hollow Knight",
                            cover_url="https://img/hk.jpg",
                            summary="A bug adventure.",
                            genres=["Metroidvania"],
                            first_release_date=date(2017, 2, 24),
                        )
                    ]
                }
            )
            report = await backfill_games(game_repo=repo, igdb_client=client, min_score=0.6)

            assert len(report.enriched) == 1
            assert report.enriched[0].igdb_title == "Hollow Knight"
            enriched = await repo.get_by_id(game_id)
            assert enriched is not None
            assert enriched.igdb_id == 1
            assert enriched.genres == ["Metroidvania"]
            assert enriched.cover_url == "https://img/hk.jpg"
            assert enriched.metadata_source == "igdb"

    async def test_dry_run_writes_nothing(self) -> None:
        async with _TestSessionFactory() as session:
            repo = GameRepository(session)
            game_id = await _make_game(repo, title="Celeste")
            await session.flush()

            client = FakeIGDBClient(
                {"Celeste": [IGDBGame(igdb_id=2, title="Celeste", genres=["Platformer"])]}
            )
            report = await backfill_games(
                game_repo=repo, igdb_client=client, min_score=0.6, dry_run=True
            )

            assert len(report.matched_dry_run) == 1
            assert not report.enriched
            unchanged = await repo.get_by_id(game_id)
            assert unchanged is not None
            assert unchanged.igdb_id is None

    async def test_unmatched_when_no_candidate_clears_threshold(self) -> None:
        async with _TestSessionFactory() as session:
            repo = GameRepository(session)
            await _make_game(repo, title="Totally Obscure Title")
            await session.flush()

            client = FakeIGDBClient(
                {"Totally Obscure Title": [IGDBGame(igdb_id=9, title="Completely Different")]}
            )
            report = await backfill_games(game_repo=repo, igdb_client=client, min_score=0.6)

            assert report.unmatched == ["Totally Obscure Title"]
            assert not report.enriched

    async def test_skips_collision_with_existing_canonical_row(self) -> None:
        async with _TestSessionFactory() as session:
            repo = GameRepository(session)
            # Canonical row already owns igdb_id=3.
            await _make_game(repo, title="Hades (Canonical)", igdb_id=3)
            dup_id = await _make_game(repo, title="Hades")
            await session.flush()

            client = FakeIGDBClient({"Hades": [IGDBGame(igdb_id=3, title="Hades")]})
            report = await backfill_games(game_repo=repo, igdb_client=client, min_score=0.6)

            assert len(report.skipped_collision) == 1
            assert not report.enriched
            dup = await repo.get_by_id(dup_id)
            assert dup is not None
            assert dup.igdb_id is None  # untouched

    async def test_scanned_counts_all_outcomes(self) -> None:
        async with _TestSessionFactory() as session:
            repo = GameRepository(session)
            await _make_game(repo, title="Hollow Knight")
            await _make_game(repo, title="No Match Here")
            await session.flush()

            client = FakeIGDBClient(
                {"Hollow Knight": [IGDBGame(igdb_id=1, title="Hollow Knight")]}
            )
            report = await backfill_games(game_repo=repo, igdb_client=client, min_score=0.6)

            assert report.scanned == 2
            assert len(report.enriched) == 1
            assert report.unmatched == ["No Match Here"]


class TestEnrichGame:
    """The single-game helper shared by create_game and backfill_games."""

    async def test_enriches_and_returns_true(self) -> None:
        async with _TestSessionFactory() as session:
            repo = GameRepository(session)
            game_id = await _make_game(repo, title="Hollow Knight")
            await session.flush()
            game = await repo.get_by_id(game_id)
            assert game is not None

            client = FakeIGDBClient(
                {
                    "Hollow Knight": [
                        IGDBGame(
                            igdb_id=1,
                            title="Hollow Knight",
                            genres=["Metroidvania"],
                        )
                    ]
                }
            )
            enriched = await enrich_game(game, igdb_client=client, game_repo=repo, min_score=0.6)
            assert enriched is True
            assert game.igdb_id == 1
            assert game.genres == ["Metroidvania"]
            assert game.metadata_source == "igdb"

    async def test_no_match_returns_false(self) -> None:
        async with _TestSessionFactory() as session:
            repo = GameRepository(session)
            game_id = await _make_game(repo, title="Obscure")
            await session.flush()
            game = await repo.get_by_id(game_id)
            assert game is not None

            client = FakeIGDBClient({"Obscure": [IGDBGame(igdb_id=9, title="Different")]})
            enriched = await enrich_game(game, igdb_client=client, game_repo=repo, min_score=0.6)
            assert enriched is False
            assert game.igdb_id is None

    async def test_collision_returns_false(self) -> None:
        async with _TestSessionFactory() as session:
            repo = GameRepository(session)
            await _make_game(repo, title="Hades (Canonical)", igdb_id=3)
            dup_id = await _make_game(repo, title="Hades")
            await session.flush()
            dup = await repo.get_by_id(dup_id)
            assert dup is not None

            client = FakeIGDBClient({"Hades": [IGDBGame(igdb_id=3, title="Hades")]})
            enriched = await enrich_game(dup, igdb_client=client, game_repo=repo, min_score=0.6)
            assert enriched is False
            assert dup.igdb_id is None
