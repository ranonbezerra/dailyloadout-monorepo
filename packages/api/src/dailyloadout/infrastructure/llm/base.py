"""Abstract base class for LLM clients used in capture processing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ExtractedGame:
    """A game title extracted from user input by the LLM."""

    title: str
    platform_hint: str | None = None
    confidence: float | None = None


class AbstractLLMClient(ABC):
    """Contract for LLM clients that parse capture text into game titles."""

    @abstractmethod
    async def parse_capture_text(self, text: str) -> list[ExtractedGame]:
        """Extract game titles from free text input."""
        ...

    @abstractmethod
    async def parse_capture_image(self, image_base64: str) -> list[ExtractedGame]:
        """Extract game titles from a photo (cover or shelf)."""
        ...
