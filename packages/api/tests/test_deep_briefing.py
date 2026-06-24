"""Tests for the deep-research briefing agent: nodes, router, graph, agent."""

from __future__ import annotations

import time

import pytest

from dailyloadout.config import Settings
from dailyloadout.infrastructure.agent.base import BriefResult, DeepBriefRequest
from dailyloadout.infrastructure.agent.dummy import DummyBriefingAgent
from dailyloadout.infrastructure.agent.factory import get_briefing_agent
from dailyloadout.infrastructure.agent.graph import nodes
from dailyloadout.infrastructure.agent.graph.builder import build_graph, route_after_grade
from dailyloadout.infrastructure.agent.graph.state import MissionContext
from dailyloadout.infrastructure.agent.langgraph_agent import LangGraphBriefingAgent
from dailyloadout.infrastructure.llm.dummy import DummyLLMClient
from dailyloadout.infrastructure.research.base import AbstractResearchClient
from dailyloadout.infrastructure.research.dummy import DummyResearchClient, EmptyResearchClient

FUTURE = float("inf")


def _ctx(**overrides: object) -> MissionContext:
    base: dict[str, object] = {
        "game_title": "Hollow Knight",
        "location": "Greenpath",
        "current_quest": None,
        "next_action": "find Cornifer",
        "level": None,
        "previous_debriefs": [{"location": "Greenpath", "raw_text": "got lost"}],
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
        self.briefing_calls = 0

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

    async def generate_briefing(self, *args: object, **kwargs: object) -> str:  # type: ignore[override]
        self.briefing_calls += 1
        return "QUICK FALLBACK BRIEFING"


def _settings(**kw: object) -> Settings:
    defaults: dict[str, object] = {
        "deep_briefing_max_refines": 2,
        "deep_briefing_max_results": 6,
        "deep_briefing_deadline_seconds": 60,
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

    async def test_spoiler_filter_returns_filtered(self) -> None:
        out = await nodes.spoiler_filter(
            {"context": _ctx(), "draft": "raw"}, llm=ScriptedLLM(filtered="SAFE TEXT")
        )
        assert out["filtered"] == "SAFE TEXT"

    async def test_anti_hallucination_grounded_not_suspicious(self) -> None:
        state = {
            "context": _ctx(),
            "filtered": "Explore Greenpath",
            "results": [{"title": "t", "url": "u", "snippet": "Greenpath area"}],
        }
        out = await nodes.anti_hallucination(state)
        assert out["suspicious"] is False
        assert out["source"] == "deep_research"
        assert "Heads up" not in out["briefing"]

    async def test_anti_hallucination_ungrounded_appends_disclaimer(self) -> None:
        state = {
            "context": _ctx(location=None, previous_debriefs=[]),
            "filtered": "Defeat Radahn in Caelid then visit Sellia",
            "results": [{"title": "t", "url": "u", "snippet": "nothing relevant"}],
        }
        out = await nodes.anti_hallucination(state)
        assert out["suspicious"] is True
        assert "Heads up" in out["briefing"]

    async def test_fallback_quick_uses_generate_briefing(self) -> None:
        llm = ScriptedLLM()
        out = await nodes.fallback_quick({"context": _ctx()}, llm=llm)
        assert out["source"] == "quick_fallback"
        assert out["briefing"] == "QUICK FALLBACK BRIEFING"
        assert llm.briefing_calls == 1


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
        assert final["briefing"]

    async def test_refine_once_then_succeed(self) -> None:
        llm = ScriptedLLM(grades=["insufficient", "sufficient"])
        final = await _run(llm, DummyResearchClient(), _settings(deep_briefing_max_refines=2))
        assert final["source"] == "deep_research"
        assert final["refine_count"] == 1

    async def test_refine_exhausted_falls_back(self) -> None:
        llm = ScriptedLLM(grades=["insufficient", "insufficient"])
        final = await _run(llm, DummyResearchClient(), _settings(deep_briefing_max_refines=1))
        assert final["source"] == "quick_fallback"
        assert final["briefing"] == "QUICK FALLBACK BRIEFING"

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

    async def test_spoiler_filter_output_is_used_not_draft(self) -> None:
        """The final briefing comes from the filtered text, never the raw draft."""
        llm = ScriptedLLM(
            draft="Defeat the Hollow Knight boss in the Black Egg Temple",
            filtered="Head to the temple area and continue exploring Greenpath",
        )
        final = await _run(llm, DummyResearchClient(), _settings())
        assert "boss" not in final["briefing"]
        assert "Head to the temple" in final["briefing"]


# ---------------------------------------------------------------------------
# Agent + factory tests
# ---------------------------------------------------------------------------


class TestAgents:
    async def test_langgraph_agent_returns_brief_result(self) -> None:
        agent = LangGraphBriefingAgent(
            llm=DummyLLMClient(), research=DummyResearchClient(), settings=_settings()
        )
        result = await agent.deep_brief(DeepBriefRequest(context=_ctx(), thread_id="m1"))
        assert isinstance(result, BriefResult)
        assert result.source in ("deep_research", "quick_fallback")
        assert result.text

    async def test_dummy_agent_returns_canned(self) -> None:
        result = await DummyBriefingAgent().deep_brief(
            DeepBriefRequest(context=_ctx(), thread_id="m1")
        )
        assert result.source == "deep_research"
        assert "Hollow Knight" in result.text
        assert result.suspicious is False

    def test_factory_dummy(self) -> None:
        agent = get_briefing_agent(Settings(agent_provider="dummy"), DummyLLMClient())
        assert isinstance(agent, DummyBriefingAgent)

    def test_factory_langgraph(self) -> None:
        agent = get_briefing_agent(
            Settings(agent_provider="langgraph", research_provider="dummy"), DummyLLMClient()
        )
        assert isinstance(agent, LangGraphBriefingAgent)

    def test_factory_unknown_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown agent provider"):
            get_briefing_agent(Settings(agent_provider="bogus"), DummyLLMClient())
