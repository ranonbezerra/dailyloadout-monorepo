"""Wire the deep-research briefing graph: nodes, edges, router, checkpointer."""

from __future__ import annotations

import time
from functools import partial
from typing import TYPE_CHECKING

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from . import nodes
from .state import ResearchBriefingState

if TYPE_CHECKING:
    from dailyloadout.config import Settings
    from dailyloadout.infrastructure.llm.base import AbstractLLMClient
    from dailyloadout.infrastructure.research.base import AbstractResearchClient


def route_after_grade(state: ResearchBriefingState, *, max_refines: int) -> str:
    """Decide where to go after grading: synthesize, refine, or fall back.

    Two independent stops keep the loop bounded: the wall-clock deadline and
    the refine counter.
    """
    if time.monotonic() > state["deadline_ts"]:
        return "fallback_quick"
    grade = state.get("grade")
    if grade == "sufficient":
        return "synthesize"
    if grade == "insufficient" and state.get("refine_count", 0) < max_refines:
        return "refine_query"
    return "fallback_quick"  # empty, or refines exhausted


def build_graph(
    *,
    llm: AbstractLLMClient,
    research: AbstractResearchClient,
    settings: Settings,
) -> object:
    """Compile the briefing graph with its dependencies bound to each node."""
    graph: StateGraph[ResearchBriefingState] = StateGraph(ResearchBriefingState)

    graph.add_node("build_query", nodes.build_query)
    graph.add_node(
        "search",
        partial(nodes.search, research=research, max_results=settings.deep_briefing_max_results),
    )
    graph.add_node("grade_results", partial(nodes.grade_results, llm=llm))
    graph.add_node("refine_query", partial(nodes.refine_query, llm=llm))
    graph.add_node(
        "synthesize",
        partial(
            nodes.synthesize,
            llm=llm,
            research=research,
            scrape_top_n=settings.deep_briefing_scrape_top_n,
        ),
    )
    graph.add_node("spoiler_filter", partial(nodes.spoiler_filter, llm=llm))
    graph.add_node("anti_hallucination", nodes.anti_hallucination)
    graph.add_node("fallback_quick", partial(nodes.fallback_quick, llm=llm))

    graph.add_edge(START, "build_query")
    graph.add_edge("build_query", "search")
    graph.add_edge("search", "grade_results")
    graph.add_conditional_edges(
        "grade_results",
        partial(route_after_grade, max_refines=settings.deep_briefing_max_refines),
        {
            "synthesize": "synthesize",
            "refine_query": "refine_query",
            "fallback_quick": "fallback_quick",
        },
    )
    graph.add_edge("refine_query", "search")  # the bounded loop
    graph.add_edge("synthesize", "spoiler_filter")
    graph.add_edge("spoiler_filter", "anti_hallucination")
    graph.add_edge("anti_hallucination", END)
    graph.add_edge("fallback_quick", END)

    return graph.compile(checkpointer=MemorySaver())
