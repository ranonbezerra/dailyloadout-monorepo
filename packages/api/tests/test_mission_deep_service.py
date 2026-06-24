"""Service-level tests for deep-briefing mode selection and fallback."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from dailyloadout.config import Settings
from dailyloadout.core.mission.briefing import generate_briefing_for_mode
from dailyloadout.infrastructure.agent.base import (
    AbstractBriefingAgent,
    BriefResult,
    DeepBriefRequest,
)
from dailyloadout.infrastructure.agent.dummy import DummyBriefingAgent
from dailyloadout.infrastructure.llm.dummy import DummyLLMClient
from dailyloadout.infrastructure.research.base import ResearchUnavailableError


class _FakeMissionRepo:
    async def get_pending_extractions(self, entry_id: int) -> list:
        return []

    async def get_recent_for_entry(self, entry_id: int, limit: int = 3) -> list:
        return []


class _RaisingAgent(AbstractBriefingAgent):
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def deep_brief(self, req: DeepBriefRequest) -> BriefResult:
        raise self._exc


class _EmptyTextAgent(AbstractBriefingAgent):
    async def deep_brief(self, req: DeepBriefRequest) -> BriefResult:
        return BriefResult(text="", source="deep_research", suspicious=False)


def _entry() -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        public_id=uuid4(),
        mission_next_action=None,
        game=SimpleNamespace(title="Hollow Knight"),
    )


async def _brief(agent: AbstractBriefingAgent | None, mode: str) -> str:
    return await generate_briefing_for_mode(
        _FakeMissionRepo(),  # type: ignore[arg-type]
        SimpleNamespace(),  # type: ignore[arg-type]  # library_repo unused on empty path
        DummyLLMClient(),
        agent,
        Settings(deep_briefing_deadline_seconds=60),
        _entry(),  # type: ignore[arg-type]
        mode,  # type: ignore[arg-type]
    )


def _is_quick(text: str) -> bool:
    low = text.lower()
    return "first mission" in low or "welcome" in low


class TestDeepBriefingMode:
    async def test_deep_mode_uses_agent_text(self) -> None:
        text = await _brief(DummyBriefingAgent(), "deep")
        assert "Previously on Hollow Knight" in text

    async def test_quick_mode_skips_agent(self) -> None:
        assert _is_quick(await _brief(DummyBriefingAgent(), "quick"))

    async def test_deep_without_agent_falls_back_to_quick(self) -> None:
        assert _is_quick(await _brief(None, "deep"))

    async def test_research_unavailable_falls_back(self) -> None:
        assert _is_quick(await _brief(_RaisingAgent(ResearchUnavailableError("down")), "deep"))

    async def test_timeout_falls_back(self) -> None:
        assert _is_quick(await _brief(_RaisingAgent(TimeoutError()), "deep"))

    async def test_unexpected_error_falls_back(self) -> None:
        assert _is_quick(await _brief(_RaisingAgent(RuntimeError("boom")), "deep"))

    async def test_empty_agent_text_falls_back(self) -> None:
        assert _is_quick(await _brief(_EmptyTextAgent(), "deep"))
