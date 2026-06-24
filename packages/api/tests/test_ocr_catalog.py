"""Unit tests for the OCR + catalog ports (ROADMAP Epic 14)."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import uuid4

from dailyloadout.infrastructure.catalog.dummy import DummyCatalogMatcher
from dailyloadout.infrastructure.catalog.matcher import _normalize, best_match
from dailyloadout.infrastructure.db.repositories.usage import UsageCounterRepository
from dailyloadout.infrastructure.igdb.schemas import IGDBGame
from dailyloadout.infrastructure.ocr.dummy import DummyOCRClient
from tests.conftest import _TestSessionFactory

# -- DummyOCRClient -------------------------------------------------------------


async def test_ocr_reads_one_line() -> None:
    res = await DummyOCRClient().extract_lines(b"Hollow Knight")
    assert [line.text for line in res.lines] == ["Hollow Knight"]
    assert res.mean_confidence > 0.9


async def test_ocr_reads_many_lines() -> None:
    payload = "\n".join(f"Game {i}" for i in range(40)).encode("utf-8")
    res = await DummyOCRClient().extract_lines(payload)
    assert len(res.lines) == 40

    payload100 = "\n".join(f"Title {i}" for i in range(100)).encode("utf-8")
    res100 = await DummyOCRClient().extract_lines(payload100)
    assert len(res100.lines) == 100


async def test_ocr_lowconf_marker_drops_confidence() -> None:
    res = await DummyOCRClient().extract_lines(b"__lowconf__\nBlurry Title")
    assert [line.text for line in res.lines] == ["Blurry Title"]
    assert res.mean_confidence < 0.5


async def test_ocr_skips_blank_lines() -> None:
    res = await DummyOCRClient().extract_lines(b"Celeste\n\n  \nHades")
    assert [line.text for line in res.lines] == ["Celeste", "Hades"]


# -- best_match (pure fuzzy scorer) ---------------------------------------------


def test_normalize_strips_punctuation() -> None:
    assert _normalize("Sid Meier's Civ-VI!!") == "sid meier s civ vi"


def test_best_match_corrects_dirty_title() -> None:
    candidates = [
        IGDBGame(igdb_id=1, title="Sid Meier's Civilization VI"),
        IGDBGame(igdb_id=2, title="Celeste"),
    ]
    result = best_match("Sid Meiers Civilization Vl", candidates, 0.6)
    assert result is not None
    assert result[0].title == "Sid Meier's Civilization VI"
    assert result[1] >= 0.6


def test_best_match_returns_none_below_threshold() -> None:
    candidates = [IGDBGame(igdb_id=1, title="Hollow Knight")]
    assert best_match("Totally Different Game", candidates, 0.6) is None


def test_best_match_empty_line() -> None:
    assert best_match("   ", [IGDBGame(igdb_id=1, title="Hades")], 0.6) is None


# -- DummyCatalogMatcher --------------------------------------------------------


async def test_dummy_matcher_matches_and_enriches() -> None:
    match = await DummyCatalogMatcher().match("Hollow Knight")
    assert match.matched
    assert match.title == "Hollow Knight"
    assert match.igdb_id == 1
    assert match.genres


async def test_dummy_matcher_deconfuses_ocr_glyphs() -> None:
    match = await DummyCatalogMatcher().match("Ho11ow Knight")
    assert match.matched
    assert match.title == "Hollow Knight"


async def test_dummy_matcher_echoes_unmatched() -> None:
    match = await DummyCatalogMatcher().match("Some Obscure Indie XYZ")
    assert not match.matched
    assert match.title == "Some Obscure Indie XYZ"
    assert match.igdb_id is None


async def test_dummy_matcher_match_many() -> None:
    matches = await DummyCatalogMatcher().match_many(["Celeste", "Hades"])
    assert [m.title for m in matches] == ["Celeste", "Hades"]


# -- IGDBCatalogMatcher (stubbed IGDB) ------------------------------------------


class _StubIGDB:
    def __init__(self, results: list[IGDBGame], fail: bool = False) -> None:
        self._results = results
        self._fail = fail

    async def search_games(self, query: str, limit: int = 5) -> list[IGDBGame]:
        if self._fail:
            raise RuntimeError("igdb down")
        return self._results


async def test_igdb_matcher_matches_and_enriches() -> None:
    from dailyloadout.infrastructure.catalog.matcher import IGDBCatalogMatcher

    igdb = _StubIGDB([IGDBGame(igdb_id=42, title="Hollow Knight", genres=["Metroidvania"])])
    match = await IGDBCatalogMatcher(igdb).match("Hollow Knght")  # type: ignore[arg-type]
    assert match.matched
    assert match.igdb_id == 42
    assert match.title == "Hollow Knight"


async def test_igdb_matcher_search_failure_echoes() -> None:
    from dailyloadout.infrastructure.catalog.matcher import IGDBCatalogMatcher

    match = await IGDBCatalogMatcher(_StubIGDB([], fail=True)).match("Anything")  # type: ignore[arg-type]
    assert not match.matched
    assert match.title == "Anything"


# -- UsageCounterRepository -----------------------------------------------------


async def _seed_user(session: Any) -> int:
    from dailyloadout.infrastructure.db.models import User

    user = User(email=f"{uuid4().hex}@test.com", password_hash="h", display_name="T")
    session.add(user)
    await session.flush()
    return user.id


async def test_usage_counter_increments() -> None:
    day = date(2026, 6, 24)
    async with _TestSessionFactory() as session:
        user_id = await _seed_user(session)
        repo = UsageCounterRepository(session)

        assert await repo.get_count(user_id, "imports", day) == 0
        assert await repo.increment(user_id, "imports", day, amount=3) == 3
        assert await repo.increment(user_id, "imports", day) == 4
        assert await repo.get_count(user_id, "imports", day) == 4
        # A different day is tracked separately.
        assert await repo.get_count(user_id, "imports", date(2026, 6, 25)) == 0
