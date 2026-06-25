"""Factory for the deep-research briefing agent."""

from __future__ import annotations

from typing import TYPE_CHECKING

from dailyloadout.config import Settings

from .base import AbstractBriefingAgent

if TYPE_CHECKING:
    from dailyloadout.infrastructure.llm.base import AbstractLLMClient


def get_briefing_agent(
    settings: Settings,
    llm: AbstractLLMClient,
) -> AbstractBriefingAgent | None:
    """Return the briefing agent for the configured provider, or ``None``.

    ``None`` means deep briefings are disabled and callers fall back to the
    quick path. The research client is selected from settings here so the
    agent stays the single entry point for the deep flow.
    """
    provider = settings.agent_provider

    if provider == "dummy":
        from .dummy import DummyBriefingAgent

        return DummyBriefingAgent()

    if provider == "langgraph":
        from dailyloadout.infrastructure.cache.factory import get_cache
        from dailyloadout.infrastructure.llm.cached import CachedLLMClient
        from dailyloadout.infrastructure.research.cached import CachedResearchClient
        from dailyloadout.infrastructure.research.factory import get_research_client

        from .cached import CachedBriefingAgent
        from .langgraph_agent import LangGraphBriefingAgent

        # Three layers of caching (ROADMAP Epic 18 Phase 3): the whole briefing
        # is cached by context; on a miss, the inner research + LLM-complete
        # calls are de-duped across runs that share a query or prompt.
        cache = get_cache(settings)
        research = CachedResearchClient(
            get_research_client(settings), cache, settings.research_cache_ttl_seconds
        )
        cached_llm = CachedLLMClient(llm, cache, settings.llm_cache_ttl_seconds)
        agent = LangGraphBriefingAgent(llm=cached_llm, research=research, settings=settings)
        return CachedBriefingAgent(agent, cache, settings.briefing_cache_ttl_seconds)

    msg = f"Unknown agent provider: {provider}"
    raise ValueError(msg)
