"""Factory for the Backlog Concierge agent."""

from __future__ import annotations

from slate.config import Settings

from .base import AbstractConciergeAgent


def get_concierge_agent(settings: Settings) -> AbstractConciergeAgent:
    """Return the Concierge agent for the configured provider.

    Defaults to the deterministic dummy (also used in tests/CI) so the
    tool-calling model is never required unless explicitly enabled.
    """
    if settings.app_env == "testing" or settings.concierge_provider == "dummy":
        from .dummy import DummyConciergeAgent

        return DummyConciergeAgent()

    if settings.concierge_provider == "langgraph":
        from .langgraph_agent import LangGraphConciergeAgent

        return LangGraphConciergeAgent(settings=settings)

    msg = f"Unknown concierge provider: {settings.concierge_provider}"
    raise ValueError(msg)
