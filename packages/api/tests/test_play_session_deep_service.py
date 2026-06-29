"""Service-level tests for deep-recap mode selection and fallback."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from slate.config import Settings
from slate.core.play_session.recap import generate_recap_for_mode
from slate.infrastructure.agent.base import (
    AbstractRecapAgent,
    DeepRecapRequest,
    RecapResult,
)
from slate.infrastructure.agent.dummy import DummyRecapAgent
from slate.infrastructure.llm.dummy import DummyLLMClient
from slate.infrastructure.research.base import ResearchUnavailableError


class _FakePlaySessionRepo:
    async def get_pending_extractions(self, entry_id: int) -> list:
        return []

    async def get_recent_for_entry(self, entry_id: int, limit: int = 3) -> list:
        return []


class _RaisingAgent(AbstractRecapAgent):
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def deep_recap(self, req: DeepRecapRequest) -> RecapResult:
        raise self._exc


class _EmptyTextAgent(AbstractRecapAgent):
    async def deep_recap(self, req: DeepRecapRequest) -> RecapResult:
        return RecapResult(text="", source="deep_research", suspicious=False)


def _entry() -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        public_id=uuid4(),
        play_session_next_action=None,
        game=SimpleNamespace(title="Hollow Knight"),
    )


async def _recap(agent: AbstractRecapAgent | None, mode: str) -> str:
    return await generate_recap_for_mode(
        _FakePlaySessionRepo(),  # type: ignore[arg-type]
        SimpleNamespace(),  # type: ignore[arg-type]  # library_repo unused on empty path
        DummyLLMClient(),
        agent,
        Settings(deep_recap_deadline_seconds=60),
        _entry(),  # type: ignore[arg-type]
        mode,  # type: ignore[arg-type]
    )


def _is_quick(text: str) -> bool:
    low = text.lower()
    return "first play_session" in low or "welcome" in low


class TestDeepRecapMode:
    async def test_deep_mode_uses_agent_text(self) -> None:
        text = await _recap(DummyRecapAgent(), "deep")
        assert "Previously on Hollow Knight" in text

    async def test_quick_mode_skips_agent(self) -> None:
        assert _is_quick(await _recap(DummyRecapAgent(), "quick"))

    async def test_deep_without_agent_falls_back_to_quick(self) -> None:
        assert _is_quick(await _recap(None, "deep"))

    async def test_research_unavailable_falls_back(self) -> None:
        assert _is_quick(await _recap(_RaisingAgent(ResearchUnavailableError("down")), "deep"))

    async def test_timeout_falls_back(self) -> None:
        assert _is_quick(await _recap(_RaisingAgent(TimeoutError()), "deep"))

    async def test_unexpected_error_falls_back(self) -> None:
        assert _is_quick(await _recap(_RaisingAgent(RuntimeError("boom")), "deep"))

    async def test_empty_agent_text_falls_back(self) -> None:
        assert _is_quick(await _recap(_EmptyTextAgent(), "deep"))
