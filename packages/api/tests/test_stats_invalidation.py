"""Stats invalidation hooks across every write seam (ROADMAP Epic 18, Phase 2).

Proves each stats-affecting mutation busts the user's stats namespace — the
auto-clamp worker, the library service (add/update/delete), and the concierge
write tools. Invalidation is ambient (the services don't take a cache), so we
monkeypatch the resolver to observe the bust with a spy. No DB or Redis.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from dailyloadout.infrastructure.cache.keys import stats_namespace


class SpyCache:
    """Records delete_namespace prefixes; behaves as an always-miss cache."""

    def __init__(self) -> None:
        self.busted: list[str] = []

    async def get_json(self, key: str) -> Any | None:
        return None

    async def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        return None

    async def delete(self, key: str) -> None:
        return None

    async def delete_namespace(self, prefix: str) -> None:
        self.busted.append(prefix)


@pytest.fixture
def spy_cache(monkeypatch: pytest.MonkeyPatch) -> SpyCache:
    """Replace the ambient cache resolver so invalidation hits the spy."""
    spy = SpyCache()
    monkeypatch.setattr(
        "dailyloadout.core.cache.invalidation.get_cache",
        lambda _settings: spy,
    )
    return spy


# ── Auto-clamp worker ────────────────────────────────────────────────────


class _StaleMission:
    def __init__(self, mission_id: int, user_id: int) -> None:
        self.id = mission_id
        self.user_id = user_id
        self.started_at = "2026-01-01T00:00:00Z"


class _ClampRepo:
    def __init__(self, stale: list[_StaleMission]) -> None:
        self._stale = stale
        self.clamped: list[int] = []

    async def get_stale_missions(self, max_hours: int) -> list[_StaleMission]:
        return self._stale

    async def auto_clamp(self, mission_id: int, max_hours: int) -> None:
        self.clamped.append(mission_id)


async def test_auto_clamp_busts_each_affected_user_once(spy_cache: SpyCache) -> None:
    from dailyloadout.workers.mission_auto_clamp import auto_clamp_stale_missions

    repo = _ClampRepo([_StaleMission(1, 7), _StaleMission(2, 7), _StaleMission(3, 9)])

    clamped = await auto_clamp_stale_missions(repo, max_hours=8)  # type: ignore[arg-type]

    assert clamped == 3
    # Two distinct users → two busts (user 7 collapsed despite two missions).
    assert sorted(spy_cache.busted) == sorted([stats_namespace(7), stats_namespace(9)])


async def test_auto_clamp_no_stale_does_not_bust(spy_cache: SpyCache) -> None:
    from dailyloadout.workers.mission_auto_clamp import auto_clamp_stale_missions

    assert await auto_clamp_stale_missions(_ClampRepo([])) == 0  # type: ignore[arg-type]
    assert spy_cache.busted == []


# ── Library service ──────────────────────────────────────────────────────


class _Entry:
    def __init__(self, user_id: int) -> None:
        self.id = 1
        self.user_id = user_id
        self.game: Any = None
        self.platform: Any = None


class _LibRepo:
    def __init__(self) -> None:
        self.entry = _Entry(user_id=5)

    async def exists(self, user_id: int, game_id: int, platform_id: int) -> bool:
        return False

    async def create(self, **kwargs: Any) -> _Entry:
        return self.entry

    async def get_by_public_id(self, public_id: Any, user_id: int) -> _Entry:
        return self.entry

    async def update(self, entry: _Entry, **fields: Any) -> _Entry:
        return entry

    async def delete(self, entry: _Entry) -> None:
        return None


class _GameRepo:
    async def get_by_public_id(self, public_id: Any) -> Any:
        return type("G", (), {"id": 1})()


class _PlatformRepo:
    async def get_by_id(self, platform_id: int) -> Any:
        return type("P", (), {"id": platform_id})()


def _library_service() -> Any:
    from dailyloadout.core.library.service import LibraryService

    return LibraryService(_GameRepo(), _LibRepo(), _PlatformRepo())  # type: ignore[arg-type]


async def test_add_to_library_busts_stats(spy_cache: SpyCache) -> None:
    await _library_service().add_to_library(5, uuid4(), platform_id=1)
    assert spy_cache.busted == [stats_namespace(5)]


async def test_update_entry_busts_stats(spy_cache: SpyCache) -> None:
    await _library_service().update_entry(5, uuid4(), status="playing")
    assert spy_cache.busted == [stats_namespace(5)]


async def test_delete_entry_busts_stats(spy_cache: SpyCache) -> None:
    await _library_service().delete_entry(5, uuid4())
    assert spy_cache.busted == [stats_namespace(5)]


# ── Concierge write tools ────────────────────────────────────────────────


class _ConciergeLibRepo:
    def __init__(self) -> None:
        self.entry = type("E", (), {"id": 1, "game": type("G", (), {"title": "Hades"})()})()

    async def get_by_public_id(self, public_id: Any, user_id: int) -> Any:
        return self.entry

    async def update(self, entry: Any, **fields: Any) -> Any:
        return entry


async def test_concierge_set_status_busts_stats(spy_cache: SpyCache) -> None:
    from dailyloadout.infrastructure.agent.concierge import tools_write

    msg = await tools_write.set_status(
        _ConciergeLibRepo(),  # type: ignore[arg-type]
        5,
        library_entry_public_id=str(uuid4()),
        status="completed",
    )
    assert "completed" in msg
    assert spy_cache.busted == [stats_namespace(5)]


# ── Capture confirm (creates library entries) ────────────────────────────


class _Candidate:
    def __init__(self) -> None:
        self.id = 1
        self.capture_id = 1
        self.status = "pending"
        self.title = "Hades"
        self.igdb_id = None
        self.igdb_title = None
        self.igdb_summary = None
        self.igdb_cover_url = None
        self.igdb_first_release_date = None
        self.igdb_genres = None


class _CaptureRepo:
    async def get_by_public_id(self, public_id: Any, user_id: int) -> Any:
        return type("C", (), {"id": 1})()

    async def update_status(self, capture_id: int, status: str) -> None:
        return None


class _CandidateRepo:
    def __init__(self) -> None:
        self._candidate = _Candidate()

    async def get_by_public_id(self, public_id: Any) -> _Candidate:
        return self._candidate

    async def update_status(self, candidate_id: int, status: str, **kwargs: Any) -> None:
        self._candidate.status = status

    async def get_all_for_capture(self, capture_id: int) -> list[_Candidate]:
        return [self._candidate]


class _CaptureGameRepo:
    async def get_by_slug(self, slug: str) -> Any:
        return None

    async def create(self, **kwargs: Any) -> Any:
        return type("G", (), {"id": 1})()


async def test_capture_confirm_busts_stats(spy_cache: SpyCache) -> None:
    from dailyloadout.core.capture.service import CaptureService

    service = CaptureService(
        _CaptureRepo(),  # type: ignore[arg-type]
        _CandidateRepo(),  # type: ignore[arg-type]
        _CaptureGameRepo(),  # type: ignore[arg-type]
        _LibRepo(),  # type: ignore[arg-type]
        _PlatformRepo(),  # type: ignore[arg-type]
    )

    await service.confirm_candidate(5, uuid4(), uuid4(), platform_id=1)

    assert spy_cache.busted == [stats_namespace(5)]
