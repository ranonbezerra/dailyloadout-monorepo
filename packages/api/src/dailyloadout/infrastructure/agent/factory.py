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
        from dailyloadout.infrastructure.research.factory import get_research_client

        from .langgraph_agent import LangGraphBriefingAgent

        research = get_research_client(settings)
        return LangGraphBriefingAgent(llm=llm, research=research, settings=settings)

    msg = f"Unknown agent provider: {provider}"
    raise ValueError(msg)
