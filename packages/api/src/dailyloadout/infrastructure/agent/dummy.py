"""Deterministic briefing agent for tests and offline development."""

from __future__ import annotations

from .base import AbstractBriefingAgent, BriefResult, DeepBriefRequest


class DummyBriefingAgent(AbstractBriefingAgent):
    """Return a canned deep-research briefing without running the graph."""

    async def deep_brief(self, req: DeepBriefRequest) -> BriefResult:
        """Return a deterministic, spoiler-safe briefing for tests."""
        title = req.context.get("game_title", "your game")
        return BriefResult(
            text=(
                f"Previously on {title}: you were making progress. "
                "Head toward the next area and continue your current objective."
            ),
            source="deep_research",
            suspicious=False,
        )
