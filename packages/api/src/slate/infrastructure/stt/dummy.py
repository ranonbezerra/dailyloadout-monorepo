"""Dummy STT client for testing."""

from __future__ import annotations

from .base import AbstractSTTClient, TranscriptionResult


class DummySTTClient(AbstractSTTClient):
    """Test stub that returns a fixed transcription."""

    def __init__(self, text: str = "got Hollow Knight and Hades for the Switch") -> None:
        self._text = text

    async def transcribe(self, audio_path: str, language: str = "pt") -> TranscriptionResult:
        """Return a canned transcription result."""
        return TranscriptionResult(
            text=self._text,
            language=language,
            duration_seconds=10.0,
        )
