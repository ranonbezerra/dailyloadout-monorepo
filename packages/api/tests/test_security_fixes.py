"""Tests for the post-audit user-abuse fixes (catalogue / import / sanitisers)."""

from __future__ import annotations

from typing import Any

import pytest

from dailyloadout.core.library import promotion
from dailyloadout.core.sanitization import sanitize_catalog_text, validate_https_url
from dailyloadout.infrastructure.catalog.base import CatalogMatch
from dailyloadout.workers import library_import_processor as proc

# ── sanitize_catalog_text ───────────────────────────────────────────────


def test_sanitize_catalog_text_strips_bidi() -> None:
    # RLO (U+202E) and zero-width space (U+200B) are dropped.
    assert sanitize_catalog_text("Doom‮EVIL") == "DoomEVIL"
    assert sanitize_catalog_text("Hal​f-Life") == "Half-Life"


def test_sanitize_catalog_text_strips_control_and_trims() -> None:
    assert sanitize_catalog_text("Tab\tand\nnewline") == "Tabandnewline"
    assert sanitize_catalog_text("  Halo  ") == "Halo"


def test_sanitize_catalog_text_keeps_normal_text() -> None:
    assert sanitize_catalog_text("Sid Meier's Civ VI") == "Sid Meier's Civ VI"


# ── validate_https_url ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("https://cdn.example.com/a.png", "https://cdn.example.com/a.png"),
        ("http://cdn.example.com/a.png", None),
        ("javascript:alert(1)", None),
        ("https://", None),
        (None, None),
    ],
)
def test_validate_https_url(value: str | None, expected: str | None) -> None:
    assert validate_https_url(value) == expected


# ── import: per-user IGDB budget on the bulk-match path (#1) ─────────────


async def test_match_within_igdb_budget_falls_back_when_spent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"n": 0}

    async def fake_budget(_user_id: int) -> bool:
        calls["n"] += 1
        return calls["n"] <= 2  # allow the first two live searches, then deny

    monkeypatch.setattr(proc, "igdb_budget_allows", fake_budget)

    class _Matcher:
        async def match(self, title: str) -> CatalogMatch:
            return CatalogMatch(
                line_text=title, matched=True, confidence=1.0, title=f"M:{title}", igdb_id=1
            )

    matches = await proc._match_within_igdb_budget(_Matcher(), ["a", "b", "c", "d"], user_id=7)

    assert [m.matched for m in matches] == [True, True, False, False]
    # Once the budget is spent the title resolves local-only (no enrichment).
    assert matches[2].title == "c" and matches[2].igdb_id is None
    # Budget is consulted exactly 3 times (the 3rd denies; the 4th is short-circuited).
    assert calls["n"] == 3


# ── catalogue promotion (#2) ────────────────────────────────────────────


class _FakeGame:
    def __init__(self) -> None:
        self.id = 1
        self.igdb_id: int | None = None
        self.is_shared = False
        self.created_by_user_id: int | None = 7


class _FakeGameRepo:
    async def update(self, game: Any, **fields: Any) -> Any:
        for key, value in fields.items():
            setattr(game, key, value)
        return game


class _FakeLibRepo:
    def __init__(self, owners: int) -> None:
        self._owners = owners

    async def count_distinct_owners(self, _game_id: int) -> int:
        return self._owners


async def _promote(game: _FakeGame, owners: int) -> None:
    await promotion.maybe_promote_to_shared(
        game,  # type: ignore[arg-type]
        user_id=7,
        game_repo=_FakeGameRepo(),  # type: ignore[arg-type]
        library_repo=_FakeLibRepo(owners),  # type: ignore[arg-type]
        igdb_client=None,
        min_score=0.6,
        threshold=5,
    )


async def test_promote_at_threshold() -> None:
    game = _FakeGame()
    await _promote(game, owners=5)
    assert game.is_shared is True


async def test_no_promote_below_threshold() -> None:
    game = _FakeGame()
    await _promote(game, owners=4)
    assert game.is_shared is False


async def test_no_promote_when_already_igdb_linked() -> None:
    game = _FakeGame()
    game.igdb_id = 99  # canonical rows are already shared
    await _promote(game, owners=999)
    assert game.is_shared is False
