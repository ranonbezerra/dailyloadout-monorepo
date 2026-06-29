"""Port for the deep-research recap agent."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from .graph.state import PlaySessionContext


@dataclass
class DeepRecapRequest:
    """Input to a deep recap run."""

    context: PlaySessionContext
    thread_id: str
    # Bypass the recap cache and recompute — deep is the on-demand "research my
    # current spot now" action, so user-initiated previews ask for a fresh run.
    force_refresh: bool = False


@dataclass
class RecapResult:
    """Output of a deep recap run."""

    text: str
    source: str  # "deep_research" | "quick_fallback"
    suspicious: bool


class AbstractRecapAgent(ABC):
    """Contract for agents that produce a web-grounded play_session recap."""

    @abstractmethod
    async def deep_recap(self, req: DeepRecapRequest) -> RecapResult:
        """Produce a deep, spoiler-safe recap for the given context."""
        ...
