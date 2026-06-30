"""Wire the deep-research recap graph: nodes, edges, router, checkpointer."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from functools import partial
from typing import TYPE_CHECKING, cast

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from slate.infrastructure.observability.tracing import span

from . import nodes
from .state import ResearchRecapState

if TYPE_CHECKING:
    from slate.config import Settings
    from slate.infrastructure.llm.base import AbstractLLMClient
    from slate.infrastructure.research.base import AbstractResearchClient


def _traced_node[NodeFn: Callable[..., Awaitable[object]]](name: str, fn: NodeFn) -> NodeFn:
    """Wrap a graph node so each invocation emits a ``graph.<name>`` span.

    Type-preserving (returns the node's own callable type) so LangGraph's
    ``add_node`` sees exactly the signature it would without tracing.
    """

    async def _run(state: ResearchRecapState) -> object:
        async with span(f"graph.{name}"):
            return await fn(state)

    return cast("NodeFn", _run)


def route_after_grade(state: ResearchRecapState, *, max_refines: int) -> str:
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
    """Compile the recap graph with its dependencies bound to each node."""
    graph: StateGraph[ResearchRecapState] = StateGraph(ResearchRecapState)

    graph.add_node("build_query", _traced_node("build_query", nodes.build_query))
    graph.add_node(
        "search",
        _traced_node(
            "search",
            partial(nodes.search, research=research, max_results=settings.deep_recap_max_results),
        ),
    )
    graph.add_node(
        "grade_results", _traced_node("grade_results", partial(nodes.grade_results, llm=llm))
    )
    graph.add_node(
        "refine_query", _traced_node("refine_query", partial(nodes.refine_query, llm=llm))
    )
    graph.add_node(
        "synthesize",
        _traced_node(
            "synthesize",
            partial(
                nodes.synthesize,
                llm=llm,
                research=research,
                scrape_top_n=settings.deep_recap_scrape_top_n,
            ),
        ),
    )
    graph.add_node(
        "anti_hallucination",
        _traced_node(
            "anti_hallucination",
            partial(nodes.anti_hallucination, threshold=settings.deep_recap_overlap_threshold),
        ),
    )
    graph.add_node(
        "fallback_quick", _traced_node("fallback_quick", partial(nodes.fallback_quick, llm=llm))
    )

    graph.add_edge(START, "build_query")
    graph.add_edge("build_query", "search")
    graph.add_edge("search", "grade_results")
    graph.add_conditional_edges(
        "grade_results",
        partial(route_after_grade, max_refines=settings.deep_recap_max_refines),
        {
            "synthesize": "synthesize",
            "refine_query": "refine_query",
            "fallback_quick": "fallback_quick",
        },
    )
    graph.add_edge("refine_query", "search")  # the bounded loop
    # Single spoiler-aware synthesis pass (the prompt bakes in the spoiler rules),
    # then the terminal anti-hallucination gate — no separate filter pass to dilute.
    graph.add_edge("synthesize", "anti_hallucination")
    graph.add_edge("anti_hallucination", END)
    graph.add_edge("fallback_quick", END)

    return graph.compile(checkpointer=MemorySaver())
