"""Process-wide STT concurrency semaphore (mirrors the Ollama one).

Whisper transcription is CPU/GPU-heavy; a burst of ``/transcribe`` requests would
oversubscribe the host and stall every in-flight call. This bounds the number of
concurrent transcriptions per worker process. The semaphore is created lazily on
first use so it binds to the running event loop (a module-import-time
``Semaphore`` would attach to the wrong/no loop), and the bound is read from
settings once, when it is first created.
"""

from __future__ import annotations

import asyncio

from dailyloadout.config import settings

_stt_semaphore: asyncio.Semaphore | None = None


def get_stt_semaphore() -> asyncio.Semaphore:
    """Return the process-wide STT concurrency semaphore (lazy-initialized)."""
    global _stt_semaphore
    if _stt_semaphore is None:
        _stt_semaphore = asyncio.Semaphore(settings.stt_max_concurrency)
    return _stt_semaphore
