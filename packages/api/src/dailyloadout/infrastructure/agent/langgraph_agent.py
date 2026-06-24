"""LangGraph-backed implementation of the briefing agent."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from .base import AbstractBriefingAgent, BriefResult, DeepBriefRequest
from .graph.builder import build_graph

if TYPE_CHECKING:
    from dailyloadout.config import Settings
    from dailyloadout.infrastructure.llm.base import AbstractLLMClient
    from dailyloadout.infrastructure.research.base import AbstractResearchClient


class LangGraphBriefingAgent(AbstractBriefingAgent):
    """Compile the research graph once and invoke it per request."""

    def __init__(
        self,
        *,
        llm: AbstractLLMClient,
        research: AbstractResearchClient,
        settings: Settings,
    ) -> None:
        self._graph: Any = build_graph(llm=llm, research=research, settings=settings)
        self._deadline = settings.deep_briefing_deadline_seconds

    async def deep_brief(self, req: DeepBriefRequest) -> BriefResult:
        """Invoke the graph; ``thread_id`` makes the run addressable."""
        init = {
            "context": req.context,
            "deadline_ts": time.monotonic() + self._deadline,
        }
        config = {"configurable": {"thread_id": req.thread_id}}
        final = await self._graph.ainvoke(init, config=config)
        return BriefResult(
            text=final["briefing"],
            source=final["source"],
            suspicious=bool(final.get("suspicious", False)),
        )
