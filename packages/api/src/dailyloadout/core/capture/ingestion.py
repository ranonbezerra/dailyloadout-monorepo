"""Upload ingestion helpers for the capture service.

Owns the cross-cutting plumbing the routers used to do inline: MIME/size guards
and the temp-file lifecycle for photo captures. Kept out of ``service.py`` so the
service file stays focused (and under the 300-line cap).
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager

from dailyloadout.api.v1._mime_helpers import guess_image_extension
from dailyloadout.config import Settings
from dailyloadout.core.capture.exceptions import InvalidUploadError


def validate_image(content_type: str | None, size_bytes: int, settings: Settings) -> None:
    """Guard a single uploaded image by MIME type and size.

    Raises:
        InvalidUploadError: If the file is not an image or exceeds the size cap.
    """
    if not content_type or not content_type.startswith("image/"):
        raise InvalidUploadError("File must be an image.")
    max_size = settings.capture_max_image_mb * 1024 * 1024
    if size_bytes > max_size:
        raise InvalidUploadError(f"Image file must be under {settings.capture_max_image_mb}MB.")


def validate_import_image(content_type: str | None, size_bytes: int, settings: Settings) -> None:
    """Guard one image from a bulk library import (different user-facing wording)."""
    if not content_type or not content_type.startswith("image/"):
        raise InvalidUploadError("All files must be images.")
    max_size = settings.capture_max_image_mb * 1024 * 1024
    if size_bytes > max_size:
        raise InvalidUploadError(f"Each image must be under {settings.capture_max_image_mb}MB.")


@contextmanager
def temp_image_file(
    contents: bytes, content_type: str | None, settings: Settings
) -> Iterator[str]:
    """Write *contents* to a temp file and yield its path, cleaning up afterward."""
    upload_dir = settings.capture_upload_dir
    os.makedirs(upload_dir, exist_ok=True)
    ext = guess_image_extension(content_type)
    with tempfile.NamedTemporaryFile(dir=upload_dir, suffix=ext, delete=False) as tmp:
        tmp.write(contents)
        image_path = tmp.name
    try:
        yield image_path
    finally:
        if os.path.exists(image_path):
            os.unlink(image_path)
