"""LangGraph-backed implementation of the recap agent."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from .base import AbstractRecapAgent, DeepRecapRequest, RecapResult
from .graph.builder import build_graph

if TYPE_CHECKING:
    from slate.config import Settings
    from slate.infrastructure.llm.base import AbstractLLMClient
    from slate.infrastructure.research.base import AbstractResearchClient


class LangGraphRecapAgent(AbstractRecapAgent):
    """Compile the research graph once and invoke it per request."""

    def __init__(
        self,
        *,
        llm: AbstractLLMClient,
        research: AbstractResearchClient,
        settings: Settings,
    ) -> None:
        self._graph: Any = build_graph(llm=llm, research=research, settings=settings)
        self._deadline = settings.deep_recap_deadline_seconds

    async def deep_recap(self, req: DeepRecapRequest) -> RecapResult:
        """Invoke the graph; ``thread_id`` makes the run addressable."""
        init = {
            "context": req.context,
            "deadline_ts": time.monotonic() + self._deadline,
        }
        config = {"configurable": {"thread_id": req.thread_id}}
        final = await self._graph.ainvoke(init, config=config)
        return RecapResult(
            text=final["recap"],
            source=final["source"],
            suspicious=bool(final.get("suspicious", False)),
        )
