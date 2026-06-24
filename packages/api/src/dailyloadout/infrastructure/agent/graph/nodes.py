"""Node functions for the deep-research briefing graph.

Each node takes the graph state and its injected dependencies (bound via
``functools.partial`` in ``builder.py``) and returns a partial state update.
The one creative node (``synthesize``) is bracketed by deterministic and
LLM-gated nodes; ``anti_hallucination`` reuses the Epic 6 validator unchanged.
"""

from __future__ import annotations

import json
import typing

import structlog

from dailyloadout.core.mission.anti_hallucination import validate_briefing
from dailyloadout.infrastructure.llm.base import AbstractLLMClient
from dailyloadout.infrastructure.research.base import AbstractResearchClient

from .render import render
from .state import Grade, MissionContext, ResearchBriefingState

logger = structlog.get_logger()

_VALID_GRADES: tuple[Grade, ...] = ("sufficient", "insufficient", "empty")


def _context_text(ctx: MissionContext) -> str:
    """Flatten the mission context into a single grounding string."""
    parts: list[str] = [ctx.get("game_title", "")]
    for key in ("location", "current_quest", "next_action", "level"):
        value = ctx.get(key)
        if value:
            parts.append(str(value))
    for debrief in ctx.get("previous_debriefs", []) or []:
        parts.extend(str(v) for v in debrief.values() if v is not None)
    return " ".join(p for p in parts if p)


async def build_query(state: ResearchBriefingState) -> dict[str, object]:
    """Build the initial search query from the mission context. Deterministic."""
    ctx = state["context"]
    base = (
        f"{ctx.get('game_title', '')} after {ctx.get('location') or ''} "
        f"{ctx.get('current_quest') or ''} next steps walkthrough spoiler-free"
    )
    return {"query": " ".join(base.split()), "refine_count": 0}


async def search(
    state: ResearchBriefingState,
    *,
    research: AbstractResearchClient,
    max_results: int,
) -> dict[str, object]:
    """Run a web search for the current query. The ``results`` reducer appends."""
    found = await research.search(state["query"], limit=max_results)
    results = [{"title": r.title, "url": r.url, "snippet": r.snippet} for r in found]
    return {"results": results}


async def grade_results(
    state: ResearchBriefingState,
    *,
    llm: AbstractLLMClient,
) -> dict[str, object]:
    """Ask the fast model whether the accumulated results are sufficient."""
    if not state.get("results"):
        return {"grade": "empty"}
    prompt = render(
        "research_grade.j2",
        query=state["query"],
        results=state["results"],
        context=state["context"],
    )
    raw = await llm.complete(prompt, role="fast", json=True)
    grade = "insufficient"
    try:
        parsed = json.loads(raw)
        candidate = parsed.get("grade") if isinstance(parsed, dict) else None
        if candidate in _VALID_GRADES:
            grade = candidate
    except (json.JSONDecodeError, AttributeError, TypeError):
        logger.warning("research_grade_parse_error", raw=raw[:200])
    return {"grade": grade}


async def refine_query(
    state: ResearchBriefingState,
    *,
    llm: AbstractLLMClient,
) -> dict[str, object]:
    """Reformulate the query for another search pass. Increments refine_count."""
    prompt = render(
        "research_refine.j2",
        query=state["query"],
        results=state["results"],
        context=state["context"],
    )
    new_query = (await llm.complete(prompt, role="fast")).strip()
    return {
        "query": new_query or state["query"],
        "refine_count": state.get("refine_count", 0) + 1,
    }


async def synthesize(
    state: ResearchBriefingState,
    *,
    llm: AbstractLLMClient,
    research: AbstractResearchClient | None = None,
    scrape_top_n: int = 0,
) -> dict[str, object]:
    """Synthesize a draft briefing (smart model).

    When *scrape_top_n* > 0 and a *research* client is given, the top results'
    pages are fetched and fed in full for richer, more specific grounding;
    otherwise synthesis falls back to the search snippets.
    """
    results = state.get("results", [])
    pages: list[dict[str, str]] = []
    if research is not None and scrape_top_n > 0:
        for r in results[:scrape_top_n]:
            content = await research.fetch(r["url"])
            if content:
                pages.append({"title": r["title"], "url": r["url"], "content": content})

    prompt = render(
        "briefing_research.j2",
        context=state["context"],
        results=results,
        pages=pages,
    )
    draft = (await llm.complete(prompt, role="smart")).strip()
    return {"draft": draft, "scraped_text": " ".join(p["content"] for p in pages)}


async def spoiler_filter(
    state: ResearchBriefingState,
    *,
    llm: AbstractLLMClient,
) -> dict[str, object]:
    """Rewrite the draft to directions/areas only — strip spoilers (smart model)."""
    prompt = render(
        "spoiler_filter.j2",
        draft=state["draft"],
        context=state["context"],
    )
    return {"filtered": (await llm.complete(prompt, role="smart")).strip()}


async def anti_hallucination(state: ResearchBriefingState) -> dict[str, object]:
    """Terminal gate: validate the filtered briefing against the grounding text.

    Reuses the Epic 6 token-overlap validator. The grounding text is the
    player's own context plus the retrieved snippets.
    """
    ctx = state["context"]
    snippets = " ".join(r["snippet"] for r in state.get("results", []))
    scraped = state.get("scraped_text", "")
    grounding = f"{_context_text(ctx)} {snippets} {scraped}".strip()

    result = validate_briefing(state["filtered"], grounding)
    text = state["filtered"]
    if result.is_suspicious:
        text += (
            "\n\n_(Heads up: this recap drifted from your notes and the sources — "
            "take it loosely.)_"
        )
    return {
        "overlap": result.overlap_ratio,
        "suspicious": result.is_suspicious,
        "briefing": text,
        "source": "deep_research",
    }


async def fallback_quick(
    state: ResearchBriefingState,
    *,
    llm: AbstractLLMClient,
) -> dict[str, object]:
    """Degrade to the existing single-shot quick briefing."""
    ctx = state["context"]
    previous_debriefs = typing.cast(
        "list[dict[str, object]]", ctx.get("previous_debriefs", []) or []
    )
    text = await llm.generate_briefing(
        game_title=ctx.get("game_title", ""),
        previous_debriefs=previous_debriefs,
        current_next_action=ctx.get("next_action"),
    )
    return {"briefing": text, "source": "quick_fallback"}
