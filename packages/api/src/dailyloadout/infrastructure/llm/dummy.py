"""Dummy LLM client for testing -- uses simple keyword matching."""

from __future__ import annotations

import re

from .base import AbstractLLMClient, ExtractedGame

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

    async def parse_capture_image(self, image_base64: str) -> list[ExtractedGame]:  # noqa: ARG002
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
