"""Port for the deep-research briefing agent."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from .graph.state import MissionContext


@dataclass
class DeepBriefRequest:
    """Input to a deep briefing run."""

    context: MissionContext
    thread_id: str


@dataclass
class BriefResult:
    """Output of a deep briefing run."""

    text: str
    source: str  # "deep_research" | "quick_fallback"
    suspicious: bool


class AbstractBriefingAgent(ABC):
    """Contract for agents that produce a web-grounded mission briefing."""

    @abstractmethod
    async def deep_brief(self, req: DeepBriefRequest) -> BriefResult:
        """Produce a deep, spoiler-safe briefing for the given context."""
        ...
