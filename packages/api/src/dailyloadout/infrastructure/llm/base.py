"""Abstract base class for LLM clients used in capture processing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

LLMRole = Literal["fast", "smart"]


@dataclass
class ExtractedGame:
    """A game title extracted from user input by the LLM."""

    title: str
    platform_hint: str | None = None
    confidence: float | None = None


@dataclass
class ExtractedState:
    """Structured state extracted from a mission debrief."""

    location: str | None = None
    next_action: str | None = None
    level: str | None = None
    current_quest: str | None = None


@dataclass
class LoadoutPick:
    """LLM's game pick for a daily loadout."""

    library_entry_public_id: str
    reasoning: str


class AbstractLLMClient(ABC):
    """Contract for LLM clients used in capture and mission processing."""

    @abstractmethod
    async def parse_capture_text(self, text: str) -> list[ExtractedGame]:
        """Extract game titles from free text input."""
        ...

    @abstractmethod
    async def parse_capture_image(self, image_base64: str) -> list[ExtractedGame]:
        """Extract game titles from a photo (cover or shelf)."""
        ...

    @abstractmethod
    async def generate_briefing(
        self,
        game_title: str,
        previous_debriefs: list[dict[str, object]],
        current_next_action: str | None = None,
        position_override: str | None = None,
    ) -> str:
        """Generate a mission briefing from previous debrief context."""
        ...

    @abstractmethod
    async def extract_debrief_state(
        self,
        game_title: str,
        debrief_text: str,
    ) -> ExtractedState:
        """Extract structured state from a user's free-text debrief."""
        ...

    @abstractmethod
    async def pick_loadout_game(
        self,
        candidates: list[dict[str, object]],
        mood: str,
        available_minutes: int,
        mental_energy: str,
        context: str | None = None,
    ) -> LoadoutPick:
        """Pick a game from *candidates* based on the user's current state."""
        ...

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        *,
        role: LLMRole = "fast",
        json: bool = False,
    ) -> str:
        """Run a single completion for an already-rendered *prompt*.

        Generic escape hatch for the deep-research agent nodes, which render
        their own Jinja prompts. *role* selects the fast or smart model;
        *json* requests JSON-formatted output. Returns the raw text response
        (empty string on backend failure).
        """
        ...
