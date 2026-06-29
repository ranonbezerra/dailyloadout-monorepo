"""STT infrastructure: abstract client, Whisper backend, and factory."""

from .base import AbstractSTTClient, TranscriptionResult
from .factory import get_stt_client

__all__ = [
    "AbstractSTTClient",
    "TranscriptionResult",
    "get_stt_client",
]
