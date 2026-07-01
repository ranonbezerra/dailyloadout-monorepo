"""Cheap pre-transcription audio-duration probe (DoS guard).

The upload byte-cap is NOT a duration bound: compressed codecs (Opus/MP3/AAC)
pack hours of audio into a few MB, and Whisper's cost scales with decoded
duration, not bytes. So before the expensive transcription we read the duration
from the container metadata *without decoding* and reject anything over the
configured ceiling. Uses PyAV (a faster-whisper dependency, always present).
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger()


def probe_audio_duration_seconds(path: str) -> float | None:
    """Return the audio duration in seconds from container metadata, or ``None``.

    Metadata-only (no full decode), so it's cheap even for long audio. Returns
    ``None`` when the duration can't be determined — an unparsable/crafted file,
    which the transcriber itself then fails fast on rather than decoding for
    minutes.
    """
    import av

    try:
        with av.open(path) as container:
            if container.duration is not None:
                return float(container.duration) / 1_000_000.0
            stream = next((s for s in container.streams if s.type == "audio"), None)
            if stream is not None and stream.duration is not None and stream.time_base is not None:
                return float(stream.duration * stream.time_base)
    except Exception as exc:
        logger.warning("audio_probe_failed", error=str(exc))
    return None
