"""Tests for the deep-research recap agent: nodes, router, graph, agent."""

from __future__ import annotations

import time

import pytest

from slate.config import Settings
from slate.infrastructure.agent.base import DeepRecapRequest, RecapResult
from slate.infrastructure.agent.dummy import DummyRecapAgent
from slate.infrastructure.agent.factory import get_recap_agent
from slate.infrastructure.agent.graph import nodes
from slate.infrastructure.agent.graph.builder import build_graph, route_after_grade
from slate.infrastructure.agent.graph.state import PlaySessionContext
from slate.infrastructure.agent.langgraph_agent import LangGraphRecapAgent
from slate.infrastructure.llm.dummy import DummyLLMClient
from slate.infrastructure.research.base import AbstractResearchClient
from slate.infrastructure.research.dummy import DummyResearchClient, EmptyResearchClient

FUTURE = float("inf")


def _ctx(**overrides: object) -> PlaySessionContext:
    base: dict[str, object] = {
        "game_title": "Hollow Knight",
        "location": "Greenpath",
        "current_quest": None,
        "next_action": "find Cornifer",
        "level": None,
        "previous_wrap_ups": [{"location": "Greenpath", "raw_text": "got lost"}],
    }
    base.update(overrides)
    return base  # type: ignore[return-value]


class ScriptedLLM(DummyLLMClient):
    """A dummy LLM whose grade responses are scripted, for loop-path tests."""

    def __init__(
        self,
        grades: list[str] | None = None,
        *,
        draft: str = "DRAFT with Greenpath",
        filtered: str = "Explore Greenpath to continue",
    ) -> None:
        self._grades = list(grades or [])
        self._draft = draft
        self._filtered = filtered
        self.recap_calls = 0

    async def complete(self, prompt: str, *, role: str = "fast", json: bool = False) -> str:  # type: ignore[override]
        low = prompt.lower()
        if "reformulate the search query" in low:
            return "refined query directions spoiler-free"
        if "clean up the recap" in low:
            return self._filtered
        if '"grade"' in low:
            grade = self._grades.pop(0) if self._grades else "sufficient"
            return f'{{"grade": "{grade}"}}'
        if "previously on" in low:
            return self._draft
        return "ok"

    async def generate_recap(self, *args: object, **kwargs: object) -> str:  # type: ignore[override]
        self.recap_calls += 1
        return "QUICK FALLBACK RECAP"


def _settings(**kw: object) -> Settings:
    defaults: dict[str, object] = {
        "deep_recap_max_refines": 2,
        "deep_recap_max_results": 6,
        "deep_recap_deadline_seconds": 60,
    }
    defaults.update(kw)
    return Settings(**defaults)


# ---------------------------------------------------------------------------
# Node unit tests
# ---------------------------------------------------------------------------


class TestNodes:
    async def test_build_query_includes_title_and_resets_count(self) -> None:
        out = await nodes.build_query({"context": _ctx()})
        assert "Hollow Knight" in out["query"]
        assert out["refine_count"] == 0

    async def test_search_converts_results_to_dicts(self) -> None:
        out = await nodes.search(
            {"query": "Hollow Knight"},
            research=DummyResearchClient(),
            max_results=6,
        )
        assert out["results"]
        assert isinstance(out["results"][0], dict)
        assert set(out["results"][0]) == {"title", "url", "snippet"}

    async def test_grade_empty_when_no_results(self) -> None:
        out = await nodes.grade_results({"results": [], "context": _ctx()}, llm=DummyLLMClient())
        assert out["grade"] == "empty"

    async def test_grade_parses_sufficient(self) -> None:
        state = {
            "results": [{"title": "t", "url": "u", "snippet": "s"}],
            "query": "q",
            "context": _ctx(),
        }
        out = await nodes.grade_results(state, llm=DummyLLMClient())
        assert out["grade"] == "sufficient"

    async def test_grade_invalid_json_defaults_insufficient(self) -> None:
        class BadLLM(DummyLLMClient):
            async def complete(self, prompt, *, role="fast", json=False):  # type: ignore[override]
                return "not json"

        state = {
            "results": [{"title": "t", "url": "u", "snippet": "s"}],
            "query": "q",
            "context": _ctx(),
        }
        out = await nodes.grade_results(state, llm=BadLLM())
        assert out["grade"] == "insufficient"

    async def test_refine_increments_count(self) -> None:
        state = {"query": "q", "results": [], "context": _ctx(), "refine_count": 0}
        out = await nodes.refine_query(state, llm=ScriptedLLM())
        assert out["refine_count"] == 1
        assert out["query"]

    async def test_synthesize_returns_draft(self) -> None:
        out = await nodes.synthesize(
            {"context": _ctx(), "results": []}, llm=ScriptedLLM(draft="DRAFT TEXT")
        )
        assert out["draft"] == "DRAFT TEXT"

    async def test_synthesize_scrapes_and_grounds_on_page_content(self) -> None:
        captured: dict[str, str] = {}

        class CapturingLLM(DummyLLMClient):
            async def complete(self, prompt, *, role="fast", json=False):  # type: ignore[override]
                captured["prompt"] = prompt
                return "DRAFT"

        state = {
            "context": _ctx(),
            "results": [{"title": "Guide", "url": "https://x.test/g", "snippet": "s"}],
        }
        out = await nodes.synthesize(
            state, llm=CapturingLLM(), research=DummyResearchClient(), scrape_top_n=1
        )
        assert out["draft"] == "DRAFT"
        # The dummy's fetched page text must reach the synthesis prompt.
        assert "locked door past the fountain" in captured["prompt"]

    async def test_synthesize_snippets_only_when_scrape_disabled(self) -> None:
        captured: dict[str, str] = {}

        class CapturingLLM(DummyLLMClient):
            async def complete(self, prompt, *, role="fast", json=False):  # type: ignore[override]
                captured["prompt"] = prompt
                return "DRAFT"

        state = {
            "context": _ctx(),
            "results": [{"title": "T", "url": "u", "snippet": "SNIPPET-XYZ"}],
        }
        await nodes.synthesize(
            state, llm=CapturingLLM(), research=DummyResearchClient(), scrape_top_n=0
        )
        assert "SNIPPET-XYZ" in captured["prompt"]
        assert "locked door past the fountain" not in captured["prompt"]

    async def test_anti_hallucination_grounded_not_suspicious(self) -> None:
        state = {
            "context": _ctx(),
            "draft": "Explore Greenpath",
            "results": [{"title": "t", "url": "u", "snippet": "Greenpath area"}],
        }
        out = await nodes.anti_hallucination(state)
        assert out["suspicious"] is False
        assert out["source"] == "deep_research"
        assert "Heads up" not in out["recap"]

    async def test_anti_hallucination_flags_ungrounded_but_keeps_text_clean(self) -> None:
        state = {
            "context": _ctx(location=None, previous_wrap_ups=[]),
            "draft": "Defeat Radahn in Caelid then visit Sellia",
            "results": [{"title": "t", "url": "u", "snippet": "nothing relevant"}],
        }
        out = await nodes.anti_hallucination(state)
        assert out["suspicious"] is True
        # No disclaimer baked into the body — the caller surfaces it as a note.
        assert out["recap"] == "Defeat Radahn in Caelid then visit Sellia"

    async def test_anti_hallucination_tolerant_threshold_passes(self) -> None:
        """A more tolerant threshold accepts thinner overlap (the deep path)."""
        state = {
            "context": _ctx(location=None, previous_wrap_ups=[]),
            "draft": "Greenpath and the City have a few connected paths",
            "results": [{"title": "t", "url": "u", "snippet": "Greenpath City area map"}],
        }
        out = await nodes.anti_hallucination(state, threshold=0.1)
        assert out["suspicious"] is False

    async def test_fallback_quick_uses_generate_recap(self) -> None:
        llm = ScriptedLLM()
        out = await nodes.fallback_quick({"context": _ctx()}, llm=llm)
        assert out["source"] == "quick_fallback"
        assert out["recap"] == "QUICK FALLBACK RECAP"
        assert llm.recap_calls == 1


# ---------------------------------------------------------------------------
# Router tests
# ---------------------------------------------------------------------------


class TestRouter:
    def test_sufficient_routes_to_synthesize(self) -> None:
        state = {"grade": "sufficient", "refine_count": 0, "deadline_ts": FUTURE}
        assert route_after_grade(state, max_refines=2) == "synthesize"

    def test_insufficient_with_refines_left_routes_to_refine(self) -> None:
        state = {"grade": "insufficient", "refine_count": 0, "deadline_ts": FUTURE}
        assert route_after_grade(state, max_refines=2) == "refine_query"

    def test_insufficient_exhausted_routes_to_fallback(self) -> None:
        state = {"grade": "insufficient", "refine_count": 2, "deadline_ts": FUTURE}
        assert route_after_grade(state, max_refines=2) == "fallback_quick"

    def test_empty_routes_to_fallback(self) -> None:
        state = {"grade": "empty", "refine_count": 0, "deadline_ts": FUTURE}
        assert route_after_grade(state, max_refines=2) == "fallback_quick"

    def test_past_deadline_routes_to_fallback(self) -> None:
        state = {"grade": "sufficient", "refine_count": 0, "deadline_ts": time.monotonic() - 1}
        assert route_after_grade(state, max_refines=2) == "fallback_quick"


# ---------------------------------------------------------------------------
# Graph integration tests
# ---------------------------------------------------------------------------


async def _run(
    llm: object,
    research: AbstractResearchClient,
    settings: Settings,
    **init: object,
) -> dict:
    graph = build_graph(llm=llm, research=research, settings=settings)  # type: ignore[arg-type]
    state = {
        "context": _ctx(),
        "deadline_ts": time.monotonic() + 60,
    }
    state.update(init)
    return await graph.ainvoke(state, config={"configurable": {"thread_id": "test"}})


class TestGraphIntegration:
    async def test_happy_path_deep_research(self) -> None:
        final = await _run(DummyLLMClient(), DummyResearchClient(), _settings())
        assert final["source"] == "deep_research"
        assert final["recap"]

    async def test_refine_once_then_succeed(self) -> None:
        llm = ScriptedLLM(grades=["insufficient", "sufficient"])
        final = await _run(llm, DummyResearchClient(), _settings(deep_recap_max_refines=2))
        assert final["source"] == "deep_research"
        assert final["refine_count"] == 1

    async def test_refine_exhausted_falls_back(self) -> None:
        llm = ScriptedLLM(grades=["insufficient", "insufficient"])
        final = await _run(llm, DummyResearchClient(), _settings(deep_recap_max_refines=1))
        assert final["source"] == "quick_fallback"
        assert final["recap"] == "QUICK FALLBACK RECAP"

    async def test_empty_results_fall_back(self) -> None:
        final = await _run(DummyLLMClient(), EmptyResearchClient(), _settings())
        assert final["source"] == "quick_fallback"

    async def test_past_deadline_falls_back(self) -> None:
        final = await _run(
            DummyLLMClient(),
            DummyResearchClient(),
            _settings(),
            deadline_ts=time.monotonic() - 1,
        )
        assert final["source"] == "quick_fallback"

    async def test_synthesis_output_is_the_final_recap(self) -> None:
        """Single-pass synthesis: the synthesized draft flows straight through to
        the recap — there is no separate spoiler-filter pass to swap it out."""
        llm = ScriptedLLM(draft="Head to the temple area and continue exploring Greenpath")
        final = await _run(llm, DummyResearchClient(), _settings())
        assert "Head to the temple" in final["recap"]
        assert final["source"] == "deep_research"


# ---------------------------------------------------------------------------
# Agent + factory tests
# ---------------------------------------------------------------------------


class TestAgents:
    async def test_langgraph_agent_returns_recap_result(self) -> None:
        agent = LangGraphRecapAgent(
            llm=DummyLLMClient(), research=DummyResearchClient(), settings=_settings()
        )
        result = await agent.deep_recap(DeepRecapRequest(context=_ctx(), thread_id="m1"))
        assert isinstance(result, RecapResult)
        assert result.source in ("deep_research", "quick_fallback")
        assert result.text

    async def test_dummy_agent_returns_canned(self) -> None:
        result = await DummyRecapAgent().deep_recap(
            DeepRecapRequest(context=_ctx(), thread_id="m1")
        )
        assert result.source == "deep_research"
        assert "Hollow Knight" in result.text
        assert result.suspicious is False

    def test_factory_dummy(self) -> None:
        agent = get_recap_agent(Settings(agent_provider="dummy"), DummyLLMClient())
        assert isinstance(agent, DummyRecapAgent)

    def test_factory_langgraph(self) -> None:
        # The langgraph agent is wrapped in the Epic 18 recap cache.
        from slate.infrastructure.agent.cached import CachedRecapAgent

        agent = get_recap_agent(
            Settings(agent_provider="langgraph", research_provider="dummy"), DummyLLMClient()
        )
        assert isinstance(agent, CachedRecapAgent)
        assert isinstance(agent._inner, LangGraphRecapAgent)

    def test_factory_unknown_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown agent provider"):
            get_recap_agent(Settings(agent_provider="bogus"), DummyLLMClient())
