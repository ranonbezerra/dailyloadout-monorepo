"""Factory for the deep-research recap agent."""

from __future__ import annotations

from typing import TYPE_CHECKING

from slate.config import Settings

from .base import AbstractRecapAgent

if TYPE_CHECKING:
    from slate.infrastructure.llm.base import AbstractLLMClient


def get_recap_agent(
    settings: Settings,
    llm: AbstractLLMClient,
) -> AbstractRecapAgent | None:
    """Return the recap agent for the configured provider, or ``None``.

    ``None`` means deep recaps are disabled and callers fall back to the
    quick path. The research client is selected from settings here so the
    agent stays the single entry point for the deep flow.
    """
    provider = settings.agent_provider

    if provider == "dummy":
        from .dummy import DummyRecapAgent

        return DummyRecapAgent()

    if provider == "langgraph":
        from slate.infrastructure.cache.factory import get_cache
        from slate.infrastructure.llm.cached import CachedLLMClient
        from slate.infrastructure.research.cached import CachedResearchClient
        from slate.infrastructure.research.factory import get_research_client

        from .cached import CachedRecapAgent
        from .langgraph_agent import LangGraphRecapAgent

        # Three layers of caching (ROADMAP Epic 18 Phase 3): the whole recap
        # is cached by context; on a miss, the inner research + LLM-complete
        # calls are de-duped across runs that share a query or prompt.
        cache = get_cache(settings)
        research = CachedResearchClient(
            get_research_client(settings), cache, settings.research_cache_ttl_seconds
        )
        cached_llm = CachedLLMClient(llm, cache, settings.llm_cache_ttl_seconds)
        agent = LangGraphRecapAgent(llm=cached_llm, research=research, settings=settings)
        return CachedRecapAgent(agent, cache, settings.recap_cache_ttl_seconds)

    msg = f"Unknown agent provider: {provider}"
    raise ValueError(msg)
