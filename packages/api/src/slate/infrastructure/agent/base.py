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
