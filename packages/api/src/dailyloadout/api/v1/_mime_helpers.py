"""MIME-type to file-extension helper functions used by capture endpoints."""

from __future__ import annotations


def guess_image_extension(content_type: str | None) -> str:
    """Map an image MIME type to a file extension."""
    mapping = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/bmp": ".bmp",
        "image/tiff": ".tiff",
        "image/heic": ".heic",
        "image/heif": ".heif",
    }
    return mapping.get(content_type or "", ".jpg")


def guess_audio_extension(content_type: str | None) -> str:
    """Map an audio MIME type to a file extension."""
    mapping = {
        "audio/webm": ".webm",
        "audio/mp4": ".m4a",
        "audio/mpeg": ".mp3",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/ogg": ".ogg",
        "audio/flac": ".flac",
    }
    return mapping.get(content_type or "", ".wav")
