"""Corrective/Adaptive RAG: evaluator, router, entitlement, auto wiring, A/B (Epic 29)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from sqlalchemy.ext.asyncio import AsyncSession

from evals.adaptive_recap import evaluate_adaptive
from slate.config import Settings
from slate.core.play_session.adaptive import (
    deep_recap_entitled,
    evaluate_local_relevance,
    route_recap,
)
from slate.core.play_session.routing import resolve_auto_mode
from slate.infrastructure.agent.dummy import DummyRecapAgent
from slate.infrastructure.db.models import Game, LibraryEntry, Platform, PlaySession, User
from slate.infrastructure.db.repositories.library import LibraryRepository
from slate.infrastructure.db.repositories.play_session import PlaySessionRepository
from slate.infrastructure.llm.dummy import DummyLLMClient
from tests.conftest import _TestSessionFactory

_NOW = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
_EMAIL = iter(f"ada{i}@x.com" for i in range(1000))

_RICH_A = {
    "location": "Stormveil Castle",
    "current_quest": "Godrick the Grafted",
    "next_action": "Explore Liurnia toward Raya Lucaria",
    "level": "42",
}
_RICH_B = {
    "location": "Night City",
    "current_quest": "Automatic Love",
    "next_action": "Meet Judy in Pacifica",
    "level": "18",
}


def _ns(wrap_up: str | None, state: dict[str, object] | None = None) -> SimpleNamespace:
    return SimpleNamespace(wrap_up_text=wrap_up, extracted_state=state)


def _settings(**kw: object) -> Settings:
    return Settings(**kw)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Pure evaluator + router (no DB)
# ---------------------------------------------------------------------------


class TestRelevanceEvaluator:
    def test_rich_history_is_correct(self) -> None:
        sessions = [_ns("cleared the castle", _RICH_A), _ns("ran the heist", _RICH_B)]
        assert evaluate_local_relevance(sessions, _settings()) == "correct"

    def test_cold_start_stays_quick(self) -> None:
        # New game / first session: no history → quick, NOT deep. A brand-new game must
        # never auto-escalate to the expensive web path (the cost guard).
        assert evaluate_local_relevance([], _settings()) == "correct"

    def test_thin_history_is_incorrect(self) -> None:
        # Played, but the note carries no concrete tokens → deep can augment.
        assert evaluate_local_relevance([_ns("played a bit")], _settings()) == "incorrect"

    def test_borderline_history_is_ambiguous(self) -> None:
        # 6 distinct proper nouns: >= sparse floor (5), < rich min (12) → ambiguous.
        state = {
            "location": "Stormveil Castle Margit",
            "current_quest": "Godrick Limgrave Liurnia",
        }
        assert evaluate_local_relevance([_ns("note", state)], _settings()) == "ambiguous"


class TestRouter:
    def test_correct_stays_quick(self) -> None:
        assert route_recap("correct", entitled_to_deep=True) == "quick"

    def test_incorrect_escalates_to_deep_when_entitled(self) -> None:
        assert route_recap("incorrect", entitled_to_deep=True) == "deep"

    def test_ambiguous_escalates_to_deep_when_entitled(self) -> None:
        assert route_recap("ambiguous", entitled_to_deep=True) == "deep"

    def test_unentitled_user_is_never_escalated(self) -> None:
        # The hard constraint: a free-tier user is never auto-routed to the paid deep path.
        assert route_recap("incorrect", entitled_to_deep=False) == "quick"
        assert route_recap("ambiguous", entitled_to_deep=False) == "quick"
        assert route_recap("correct", entitled_to_deep=False) == "quick"

    def test_entitlement_default_reads_setting(self) -> None:
        assert deep_recap_entitled(_settings(adaptive_deep_entitled_default=True)) is True
        assert deep_recap_entitled(_settings(adaptive_deep_entitled_default=False)) is False


# ---------------------------------------------------------------------------
# DB integration: the router over real retrieved history
# ---------------------------------------------------------------------------


async def _fixtures(session: AsyncSession) -> tuple[User, LibraryEntry]:
    user = User(email=next(_EMAIL), display_name="ada")
    game = Game(slug="elden-ring", title="Elden Ring", metadata_source="user")
    platform = Platform(slug="pc", label="PC", family="pc")
    session.add_all([user, game, platform])
    await session.flush()
    entry = LibraryEntry(
        user_id=user.id, game_id=game.id, platform_id=platform.id, status="playing"
    )
    session.add(entry)
    await session.flush()
    return user, entry


async def _seed(
    session: AsyncSession, user: User, entry: LibraryEntry, text: str, state: dict[str, object]
) -> None:
    session.add(
        PlaySession(
            user_id=user.id,
            library_entry_id=entry.id,
            play_session_type="regular",
            started_at=_NOW - timedelta(hours=2),
            ended_at=_NOW,
            ended_via="wrap_up_completed",
            wrap_up_text=text,
            extracted_state=state,
        )
    )
    await session.flush()


async def _resolve(entry_id: int, *, enabled: bool, entitled: bool) -> str:
    async with _TestSessionFactory() as s:
        entry = await s.get(LibraryEntry, entry_id)
        assert entry is not None
        return await resolve_auto_mode(
            PlaySessionRepository(s),
            LibraryRepository(s),
            DummyLLMClient(),
            _settings(adaptive_recap_enabled=enabled),
            entry,
            agent=DummyRecapAgent(),
            entitled_to_deep=entitled,
        )


class TestResolveAutoMode:
    async def test_rich_history_routes_quick(self) -> None:
        async with _TestSessionFactory() as s:
            user, entry = await _fixtures(s)
            await _seed(s, user, entry, "cleared the castle", _RICH_A)
            await _seed(s, user, entry, "ran the heist", _RICH_B)
            await s.commit()
        assert await _resolve(entry.id, enabled=True, entitled=True) == "quick"

    async def test_sparse_history_routes_deep(self) -> None:
        async with _TestSessionFactory() as s:
            user, entry = await _fixtures(s)
            await _seed(s, user, entry, "played a bit", {"location": "somewhere"})
            await s.commit()
        assert await _resolve(entry.id, enabled=True, entitled=True) == "deep"

    async def test_sparse_history_unentitled_stays_quick(self) -> None:
        """Entitlement DoD: a free-tier user is provably never auto-routed to deep."""
        async with _TestSessionFactory() as s:
            user, entry = await _fixtures(s)
            await _seed(s, user, entry, "played a bit", {"location": "somewhere"})
            await s.commit()
        assert await _resolve(entry.id, enabled=True, entitled=False) == "quick"

    async def test_new_game_cold_start_routes_quick(self) -> None:
        # No prior sessions at all → a new game must stay quick (never auto-deep). This
        # is the cost guard: adding games shouldn't fan out into expensive web research.
        async with _TestSessionFactory() as s:
            _, entry = await _fixtures(s)
            await s.commit()
        assert await _resolve(entry.id, enabled=True, entitled=True) == "quick"

    async def test_disabled_flag_stays_quick(self) -> None:
        async with _TestSessionFactory() as s:
            user, entry = await _fixtures(s)
            await _seed(s, user, entry, "played a bit", {"location": "somewhere"})
            await s.commit()
        assert await _resolve(entry.id, enabled=False, entitled=True) == "quick"


# ---------------------------------------------------------------------------
# Eval A/B (Epic 23): adaptive beats always-quick on grounding, always-deep on cost
# ---------------------------------------------------------------------------


class TestAdaptiveEval:
    def test_router_picks_the_ideal_path(self) -> None:
        assert evaluate_adaptive(_settings()).router_accuracy == 1.0

    def test_beats_always_quick_on_grounding_and_always_deep_on_cost(self) -> None:
        report = evaluate_adaptive(_settings())
        # No grounding loss vs always-deep...
        assert report.adaptive_grounding == report.always_deep_grounding
        # ...a faithfulness win over always-quick (which under-grounds the sparse cases)...
        assert report.adaptive_grounding > report.always_quick_grounding
        # ...and a cost win over always-deep (deep fires only on the sparse cases).
        assert report.adaptive_cost < report.always_deep_cost
