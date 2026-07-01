"""Node functions for the deep-research recap graph.

Each node takes the graph state and its injected dependencies (bound via
``functools.partial`` in ``builder.py``) and returns a partial state update.
The one creative node (``synthesize``) is bracketed by deterministic and
LLM-gated nodes; ``anti_hallucination`` reuses the Epic 6 validator unchanged.
"""

from __future__ import annotations

import json
import time
import typing

import structlog

from slate.core.play_session.anti_hallucination import validate_recap
from slate.infrastructure.llm.base import AbstractLLMClient
from slate.infrastructure.research.base import AbstractResearchClient

from .render import render
from .state import Grade, PlaySessionContext, ResearchRecapState, SearchResultDict

logger = structlog.get_logger()

_VALID_GRADES: tuple[Grade, ...] = ("sufficient", "insufficient", "empty")


def _context_text(ctx: PlaySessionContext) -> str:
    """Flatten the play_session context into a single grounding string."""
    parts: list[str] = [ctx.get("game_title", "")]
    for key in ("location", "current_quest", "next_action", "level"):
        value = ctx.get(key)
        if value:
            parts.append(str(value))
    for wrap_up in ctx.get("previous_wrap_ups", []) or []:
        parts.extend(str(v) for v in wrap_up.values() if v is not None)
    return " ".join(p for p in parts if p)


async def build_query(state: ResearchRecapState) -> dict[str, object]:
    """Build the initial search query from the play_session context. Deterministic.

    Targets area/geography pages ("where to go next", "area guide", "wiki")
    rather than full "walkthrough" pages — the latter are spoiler-dense and
    SEO-noisy, which pollutes the scraped grounding. The synthesis prompt mines
    these for area names and directions only.
    """
    ctx = state["context"]
    base = (
        f"{ctx.get('game_title', '')} {ctx.get('location') or ''} "
        f"{ctx.get('current_quest') or ''} where to go next area guide wiki"
    )
    return {"query": " ".join(base.split()), "refine_count": 0}


async def search(
    state: ResearchRecapState,
    *,
    research: AbstractResearchClient,
    max_results: int,
) -> dict[str, object]:
    """Run a web search for the current query. The ``results`` reducer appends."""
    found = await research.search(state["query"], limit=max_results)
    results = [{"title": r.title, "url": r.url, "snippet": r.snippet} for r in found]
    return {"results": results}


async def grade_results(
    state: ResearchRecapState,
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
    state: ResearchRecapState,
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


def _reorder(results: list[SearchResultDict], order: list[object]) -> list[SearchResultDict]:
    """Apply *order* (a list of indices) to *results*, keeping every item once.

    Invalid, duplicate, or out-of-range indices are dropped; any results the
    model failed to mention are appended in their original order, so nothing is
    silently lost — the node only ever *reorders*.
    """
    seen: set[int] = set()
    ordered: list[SearchResultDict] = []
    for i in order:
        if isinstance(i, int) and 0 <= i < len(results) and i not in seen:
            seen.add(i)
            ordered.append(results[i])
    ordered.extend(r for j, r in enumerate(results) if j not in seen)
    return ordered


async def rerank(
    state: ResearchRecapState,
    *,
    llm: AbstractLLMClient,
    enabled: bool = True,
    top_n: int = 4,
) -> dict[str, object]:
    """Reorder retrieved results by task relevance before synthesis (Epic 25).

    The ``fast`` model scores which results best match the player's situation;
    the top *top_n* become ``ranked_results``, which ``synthesize`` prefers (and
    scrapes first). Deterministic guards downstream are unchanged.

    Degrades cleanly: disabled, past the deadline, ≤1 result, or an unparsable
    response all skip the rerank and leave the raw ``results`` order in place.
    """
    results = state.get("results", [])
    if not enabled or len(results) <= 1:
        return {}
    if time.monotonic() > state.get("deadline_ts", float("inf")):
        logger.info("research_rerank_skipped_deadline")
        return {}

    prompt = render("research_rerank.j2", results=results, context=state["context"])
    raw = await llm.complete(prompt, role="fast", json=True)
    try:
        parsed = json.loads(raw)
        order = parsed.get("order") if isinstance(parsed, dict) else None
        if not isinstance(order, list):
            raise ValueError("missing 'order' array")
    except (json.JSONDecodeError, AttributeError, TypeError, ValueError):
        logger.warning("research_rerank_parse_error", raw=raw[:200])
        return {}

    return {"ranked_results": _reorder(results, order)[:top_n]}


async def synthesize(
    state: ResearchRecapState,
    *,
    llm: AbstractLLMClient,
    research: AbstractResearchClient | None = None,
    scrape_top_n: int = 0,
) -> dict[str, object]:
    """Synthesize a draft recap (smart model).

    When *scrape_top_n* > 0 and a *research* client is given, the top results'
    pages are fetched and fed in full for richer, more specific grounding;
    otherwise synthesis falls back to the search snippets. Prefers the
    rerank-ordered ``ranked_results`` (Epic 25) when present.
    """
    results = state.get("ranked_results") or state.get("results", [])
    pages: list[dict[str, str]] = []
    if research is not None and scrape_top_n > 0:
        for r in results[:scrape_top_n]:
            content = await research.fetch(r["url"])
            if content:
                pages.append({"title": r["title"], "url": r["url"], "content": content})

    prompt = render(
        "recap_research.j2",
        context=state["context"],
        results=results,
        pages=pages,
    )
    draft = (await llm.complete(prompt, role="smart")).strip()
    return {"draft": draft, "scraped_text": " ".join(p["content"] for p in pages)}


async def anti_hallucination(
    state: ResearchRecapState, *, threshold: float = 0.4
) -> dict[str, object]:
    """Terminal gate: validate the synthesized recap against the grounding text.

    Reuses the Epic 6 token-overlap validator. The grounding text is the
    player's own context plus the retrieved snippets and any scraped page text.
    *threshold* is more tolerant than the quick path: the deep recap legitimately
    surfaces real area/ability names grounded in research the verbatim overlap
    can't fully capture.
    """
    ctx = state["context"]
    snippets = " ".join(r["snippet"] for r in state.get("results", []))
    scraped = state.get("scraped_text", "")
    grounding = f"{_context_text(ctx)} {snippets} {scraped}".strip()

    draft = state["draft"]
    result = validate_recap(draft, grounding, threshold=threshold)
    # The recap text stays clean — the caller surfaces *suspicious* as a discreet
    # note rather than baking a disclaimer into the body.
    return {
        "overlap": result.overlap_ratio,
        "suspicious": result.is_suspicious,
        "recap": draft,
        "source": "deep_research",
    }


async def fallback_quick(
    state: ResearchRecapState,
    *,
    llm: AbstractLLMClient,
) -> dict[str, object]:
    """Degrade to the existing single-shot quick recap."""
    ctx = state["context"]
    previous_wrap_ups = typing.cast(
        "list[dict[str, object]]", ctx.get("previous_wrap_ups", []) or []
    )
    text = await llm.generate_recap(
        game_title=ctx.get("game_title", ""),
        previous_wrap_ups=previous_wrap_ups,
        current_next_action=ctx.get("next_action"),
    )
    return {"recap": text, "source": "quick_fallback"}
