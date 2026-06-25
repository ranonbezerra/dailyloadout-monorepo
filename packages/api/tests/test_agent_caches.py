"""Tests for the Phase 3 content-addressed caches (ROADMAP Epic 18).

The deep-briefing agent, the research client, and the LLM ``complete()`` escape
hatch — each wrapped by a caching decorator. Exercised with a fake inner + the
in-memory fake cache; no Redis, no real model.
"""

from __future__ import annotations

from typing import Any

from dailyloadout.infrastructure.agent.base import BriefResult, DeepBriefRequest
from dailyloadout.infrastructure.agent.cached import CachedBriefingAgent
from dailyloadout.infrastructure.agent.graph.state import MissionContext
from dailyloadout.infrastructure.cache.keys import briefing_key, llm_key, research_key
from dailyloadout.infrastructure.llm.cached import CachedLLMClient
from dailyloadout.infrastructure.research.base import SearchResult
from dailyloadout.infrastructure.research.cached import CachedResearchClient
from tests.test_cache_layer import FakeCache

# ── Deep-briefing cache ──────────────────────────────────────────────────


class _FakeAgent:
    def __init__(self, result: BriefResult) -> None:
        self._result = result
        self.calls = 0

    async def deep_brief(self, req: DeepBriefRequest) -> BriefResult:
        self.calls += 1
        return self._result


_CTX: MissionContext = {"game_title": "Hollow Knight", "next_action": "find the cloak"}
_REQ = DeepBriefRequest(context=_CTX, thread_id="t1")


def test_briefing_key_changes_when_context_changes() -> None:
    other: MissionContext = {**_CTX, "next_action": "beat the boss"}
    assert briefing_key("deep", _CTX) != briefing_key("deep", other)


async def test_briefing_miss_then_hit_round_trips() -> None:
    inner = _FakeAgent(BriefResult(text="Go north.", source="deep_research", suspicious=False))
    agent = CachedBriefingAgent(inner, FakeCache(), ttl_seconds=100)

    await agent.deep_brief(_REQ)
    second = await agent.deep_brief(_REQ)

    assert inner.calls == 1  # second served from cache
    assert second.text == "Go north."
    assert second.source == "deep_research"
    assert second.suspicious is False


async def test_briefing_quick_fallback_not_cached() -> None:
    inner = _FakeAgent(BriefResult(text="meh", source="quick_fallback", suspicious=False))
    agent = CachedBriefingAgent(inner, FakeCache(), ttl_seconds=100)

    await agent.deep_brief(_REQ)
    await agent.deep_brief(_REQ)

    assert inner.calls == 2  # degraded result never stored


async def test_briefing_empty_text_not_cached() -> None:
    inner = _FakeAgent(BriefResult(text="", source="deep_research", suspicious=False))
    agent = CachedBriefingAgent(inner, FakeCache(), ttl_seconds=100)

    await agent.deep_brief(_REQ)
    await agent.deep_brief(_REQ)

    assert inner.calls == 2


# ── Research cache ───────────────────────────────────────────────────────


class _FakeResearch:
    def __init__(self, results: list[SearchResult]) -> None:
        self._results = results
        self.calls = 0

    async def search(self, query: str, limit: int = 6) -> list[SearchResult]:
        self.calls += 1
        return self._results

    async def fetch(self, url: str) -> str:
        return "page body"


_RESULTS = [SearchResult(title="Wiki", url="https://w/x", snippet="go north")]


def test_research_key_is_normalized() -> None:
    assert research_key("  Hollow Knight ", 6) == "research:6:hollow knight"
    assert research_key("hk", 3) != research_key("hk", 6)


async def test_research_miss_then_hit_round_trips() -> None:
    inner = _FakeResearch(_RESULTS)
    client = CachedResearchClient(inner, FakeCache(), ttl_seconds=100)

    await client.search("hollow knight")
    again = await client.search("hollow knight")

    assert inner.calls == 1
    assert again[0].title == "Wiki"
    assert again[0].url == "https://w/x"
    assert again[0].snippet == "go north"


async def test_research_empty_not_cached() -> None:
    inner = _FakeResearch([])
    client = CachedResearchClient(inner, FakeCache(), ttl_seconds=100)

    await client.search("obscure title")
    await client.search("obscure title")

    assert inner.calls == 2  # empty result set not remembered


async def test_research_fetch_passes_through() -> None:
    client = CachedResearchClient(_FakeResearch(_RESULTS), FakeCache(), ttl_seconds=100)
    assert await client.fetch("https://w/x") == "page body"


# ── LLM complete() cache ─────────────────────────────────────────────────


class _FakeLLM:
    def __init__(self, out: str) -> None:
        self._out = out
        self.complete_calls = 0
        self.passthrough_calls = 0

    async def complete(self, prompt: str, *, role: str = "fast", json: bool = False) -> str:
        self.complete_calls += 1
        return self._out

    async def parse_capture_text(self, text: str) -> list[Any]:
        self.passthrough_calls += 1
        return []


def test_llm_key_varies_by_role_and_json() -> None:
    assert llm_key("complete", "fast", False, "p") != llm_key("complete", "smart", False, "p")
    assert llm_key("complete", "fast", False, "p") != llm_key("complete", "fast", True, "p")


async def test_complete_miss_then_hit() -> None:
    inner = _FakeLLM("answer")
    client = CachedLLMClient(inner, FakeCache(), ttl_seconds=100)  # type: ignore[arg-type]

    a = await client.complete("prompt", role="smart")
    b = await client.complete("prompt", role="smart")

    assert (a, b) == ("answer", "answer")
    assert inner.complete_calls == 1


async def test_complete_empty_not_cached() -> None:
    inner = _FakeLLM("")
    client = CachedLLMClient(inner, FakeCache(), ttl_seconds=100)  # type: ignore[arg-type]

    await client.complete("prompt")
    await client.complete("prompt")

    assert inner.complete_calls == 2


async def test_complete_distinct_role_recomputes() -> None:
    inner = _FakeLLM("answer")
    client = CachedLLMClient(inner, FakeCache(), ttl_seconds=100)  # type: ignore[arg-type]

    await client.complete("prompt", role="fast")
    await client.complete("prompt", role="smart")  # different key

    assert inner.complete_calls == 2


async def test_llm_passthrough_delegates() -> None:
    inner = _FakeLLM("answer")
    client = CachedLLMClient(inner, FakeCache(), ttl_seconds=100)  # type: ignore[arg-type]

    await client.parse_capture_text("got hades")

    assert inner.passthrough_calls == 1
