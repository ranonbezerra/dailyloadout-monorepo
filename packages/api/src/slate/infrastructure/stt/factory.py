"""Factory for STT client selection."""

from __future__ import annotations

from slate.config import Settings

from .base import AbstractSTTClient


def get_stt_client(settings: Settings) -> AbstractSTTClient:
    """Return the STT client based on the configured provider."""
    provider = settings.stt_provider

    if provider == "dummy":
        from slate.infrastructure.stt.dummy import DummySTTClient

        return DummySTTClient()

    if provider == "whisper":
        from slate.infrastructure.stt.whisper import WhisperSTTClient

        return WhisperSTTClient(settings)

    msg = f"Unknown STT provider: {provider}"
    raise ValueError(msg)
