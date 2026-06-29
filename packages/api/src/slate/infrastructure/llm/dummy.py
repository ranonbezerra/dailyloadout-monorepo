"""Dummy LLM client for testing -- uses simple keyword matching."""

from __future__ import annotations

import re
from uuid import uuid4

from .base import AbstractLLMClient, ExtractedGame, ExtractedState, LLMRole, PickSelection

# Well-known titles used for deterministic test matching.
_KNOWN_TITLES: list[tuple[str, re.Pattern[str]]] = [
    ("Hollow Knight", re.compile(r"hollow\s*knight", re.IGNORECASE)),
    ("Elden Ring", re.compile(r"elden\s*ring", re.IGNORECASE)),
    ("Zelda: Tears of the Kingdom", re.compile(r"zelda|totk|tears\s*of", re.IGNORECASE)),
    ("God of War", re.compile(r"god\s*of\s*war", re.IGNORECASE)),
    ("Hades", re.compile(r"\bhades\b", re.IGNORECASE)),
    ("Celeste", re.compile(r"\bceleste\b", re.IGNORECASE)),
    ("Stardew Valley", re.compile(r"stardew", re.IGNORECASE)),
    ("The Witcher 3", re.compile(r"witcher", re.IGNORECASE)),
    ("Dark Souls", re.compile(r"dark\s*souls", re.IGNORECASE)),
    ("Persona 5", re.compile(r"persona", re.IGNORECASE)),
]


class DummyLLMClient(AbstractLLMClient):
    """Deterministic LLM client for tests -- returns matches from a fixed title list."""

    async def parse_capture_text(self, text: str) -> list[ExtractedGame]:
        """Return ``ExtractedGame`` objects for any known titles found in *text*."""
        results: list[ExtractedGame] = []

        for title, pattern in _KNOWN_TITLES:
            if pattern.search(text):
                results.append(ExtractedGame(title=title, confidence=0.95))

        # Always return at least one result for non-empty text so tests stay useful.
        if not results and text.strip():
            # Use the first non-trivial word as a fallback title.
            words = [w for w in text.split() if len(w) > 2]
            fallback_title = words[0].capitalize() if words else "Unknown Game"
            results.append(ExtractedGame(title=fallback_title, confidence=0.5))

        return results

    async def parse_capture_image(self, image_base64: str) -> list[ExtractedGame]:
        """Return canned results simulating a shelf photo with three games."""
        return [
            ExtractedGame(
                title="The Legend of Zelda: Tears of the Kingdom",
                platform_hint="Switch",
                confidence=0.92,
            ),
            ExtractedGame(
                title="Elden Ring",
                platform_hint=None,
                confidence=0.90,
            ),
            ExtractedGame(
                title="Celeste",
                platform_hint=None,
                confidence=0.88,
            ),
        ]

    async def generate_recap(
        self,
        game_title: str,
        previous_wrap_ups: list[dict[str, object]],
        current_next_action: str | None = None,
        position_override: str | None = None,
    ) -> str:
        """Return a deterministic recap for tests."""
        if not previous_wrap_ups:
            return (
                f"Welcome to your first play_session in {game_title}! "
                "No previous session data available. Enjoy your adventure."
            )

        parts = [f"Previously on {game_title}:"]
        for wrap_up in previous_wrap_ups:
            if wrap_up.get("next_action"):
                parts.append(f"- Your next objective was: {wrap_up['next_action']}")
            if wrap_up.get("location"):
                parts.append(f"- You were at: {wrap_up['location']}")

        if position_override:
            parts.append(f"\nPlayer correction: {position_override}")

        if current_next_action:
            parts.append(f"\nSuggested next action: {current_next_action}")

        parts.append("\nWhat you could do this session:")
        parts.append("- Continue your current objective")
        parts.append("- Explore the surrounding area for hidden secrets")

        return "\n".join(parts)

    async def extract_wrap_up_state(
        self,
        game_title: str,
        wrap_up_text: str,
    ) -> ExtractedState:
        """Return a deterministic extracted state for tests."""
        return ExtractedState(
            location=None,
            next_action=wrap_up_text[:100] if wrap_up_text else None,
            level=None,
            current_quest=None,
        )

    async def select_game(
        self,
        candidates: list[dict[str, object]],
        mood: str,
        available_minutes: int,
        mental_energy: str,
        context: str | None = None,
    ) -> PickSelection:
        """Return a deterministic selection for tests.

        Special behaviour: if *mood* is ``"test_invalid_uuid"``, return a
        random UUID that is not in the candidates list, exercising the
        reroll / validation path.
        """
        if mood == "test_invalid_uuid":
            return PickSelection(
                library_entry_public_id=str(uuid4()),
                reasoning="Test invalid pick",
            )
        if not candidates:
            raise ValueError("No candidates provided")
        return PickSelection(
            library_entry_public_id=str(candidates[0]["public_id"]),
            reasoning=f"Picked {candidates[0]['game_title']} because it fits your {mood} mood.",
        )

    async def complete(
        self,
        prompt: str,
        *,
        role: LLMRole = "fast",
        json: bool = False,
    ) -> str:
        """Return canned text keyed by markers embedded in the agent prompts.

        Matches the literal phrases used in the deep-recap prompt templates
        so the graph runs deterministically in tests. Grade defaults to
        ``sufficient`` (happy path); tests needing the refine/exhausted paths
        use a purpose-built fake that scripts grade responses.
        """
        lowered = prompt.lower()
        if "reformulate the search query" in lowered:
            return "refined query: next area directions spoiler-free"
        if "clean up the recap" in lowered:
            return "Head toward the next area and finish your current objective."
        if '"grade"' in lowered:
            return '{"grade": "sufficient"}'
        if "previously on" in lowered:
            return (
                "Previously on your adventure: you were exploring. "
                "Head west to continue toward your objective."
            )
        return "ok"
