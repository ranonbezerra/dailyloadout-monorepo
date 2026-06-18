"""Base classes for Speech-to-Text clients."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TranscriptionResult:
    """Result of a speech-to-text transcription."""

    text: str
    language: str | None = None
    duration_seconds: float | None = None


class AbstractSTTClient(ABC):
    """Contract for STT clients that transcribe audio into text."""

    @abstractmethod
    async def transcribe(self, audio_path: str, language: str = "pt") -> TranscriptionResult:
        """Transcribe an audio file to text."""
        ...
