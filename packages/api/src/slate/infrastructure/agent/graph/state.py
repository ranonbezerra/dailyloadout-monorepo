"""State schema for the deep-research recap LangGraph."""

from __future__ import annotations

from operator import add
from typing import Annotated, Literal, TypedDict


class SearchResultDict(TypedDict):
    """A search result as carried in graph state (plain dict for serialization)."""

    title: str
    url: str
    snippet: str


class PlaySessionContext(TypedDict, total=False):
    """Grounding context for a recap — the same data the quick path uses."""

    game_title: str
    location: str | None
    current_quest: str | None
    next_action: str | None
    level: str | None
    previous_wrap_ups: list[dict[str, object]]


Grade = Literal["sufficient", "insufficient", "empty"]
Source = Literal["deep_research", "quick_fallback"]


class ResearchRecapState(TypedDict, total=False):
    """Working state threaded through the recap graph."""

    # --- inputs (set once at invocation) ---
    context: PlaySessionContext
    deadline_ts: float  # time.monotonic() deadline; routers compare against it

    # --- research loop working state ---
    query: str
    results: Annotated[list[SearchResultDict], add]  # reducer: accumulate across refines
    refine_count: int
    grade: Grade

    # --- synthesis + guards ---
    draft: str
    scraped_text: str  # full page text fed to synthesis; also grounds the guard
    filtered: str
    overlap: float
    suspicious: bool

    # --- output ---
    recap: str
    source: Source
