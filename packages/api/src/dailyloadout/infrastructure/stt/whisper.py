"""Whisper-backed STT client using faster-whisper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from dailyloadout.config import Settings

from .base import AbstractSTTClient, TranscriptionResult

if TYPE_CHECKING:
    from faster_whisper import WhisperModel

logger = structlog.get_logger()


class WhisperSTTClient(AbstractSTTClient):
    """STT client using faster-whisper for local transcription."""

    def __init__(self, settings: Settings) -> None:
        self._model_size = settings.whisper_model_size
        self._device = settings.whisper_device
        self._compute_type = settings.whisper_compute_type
        self._model: WhisperModel | None = None

    def _get_model(self) -> WhisperModel:
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self._model_size,
                device=self._device,
                compute_type=self._compute_type,
            )
        return self._model

    async def transcribe(self, audio_path: str, language: str = "pt") -> TranscriptionResult:
        """Transcribe audio using faster-whisper."""
        import asyncio

        model = self._get_model()

        def _run() -> tuple[str, Any]:
            segments, info = model.transcribe(
                audio_path,
                language=language,
                beam_size=5,
            )
            text = " ".join(seg.text.strip() for seg in segments)
            return text, info

        try:
            text, info = await asyncio.get_event_loop().run_in_executor(None, _run)
            return TranscriptionResult(
                text=text,
                language=info.language,
                duration_seconds=info.duration,
            )
        except Exception as exc:
            logger.warning("whisper_transcription_failed", error=str(exc))
            raise
