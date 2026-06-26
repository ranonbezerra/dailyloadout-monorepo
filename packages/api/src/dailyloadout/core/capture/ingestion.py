"""Upload ingestion helpers for the capture service.

Owns the cross-cutting plumbing the routers used to do inline: MIME/size guards
and the temp-file lifecycle for photo captures. Kept out of ``service.py`` so the
service file stays focused (and under the 300-line cap).
"""

from __future__ import annotations

import io
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime

from fastapi import UploadFile
from PIL import Image

from dailyloadout.api.v1._mime_helpers import guess_image_extension
from dailyloadout.config import Settings
from dailyloadout.core.capture.exceptions import ImportQuotaExceededError, InvalidUploadError
from dailyloadout.infrastructure.db.repositories.usage import UsageCounterRepository

# Bounded-read chunk size for capped uploads (1 MiB).
_READ_CHUNK_SIZE = 1024 * 1024
# Usage-counter key for the per-day bulk-import image cap.
_IMPORT_IMAGES_KEY = "library_import_images"


async def enforce_import_quota(
    user_id: int,
    file_count: int,
    *,
    usage_repo: UsageCounterRepository,
    settings: Settings,
) -> None:
    """Reject a bulk import on count cap + per-day quota before buffering files.

    Raises:
        InvalidUploadError: If *file_count* is empty or exceeds the per-request cap.
        ImportQuotaExceededError: If the per-day image quota would be exceeded.
    """
    if file_count < 1:
        raise InvalidUploadError("At least one image is required.")
    if file_count > settings.library_import_max_files:
        raise InvalidUploadError(
            f"Too many files: at most {settings.library_import_max_files} per import."
        )

    today = datetime.now(UTC).date()
    used = await usage_repo.get_count(user_id, _IMPORT_IMAGES_KEY, today)
    if used + file_count > settings.library_import_images_per_day:
        raise ImportQuotaExceededError("Daily library-import limit reached. Try again tomorrow.")


async def meter_import(
    user_id: int,
    file_count: int,
    *,
    usage_repo: UsageCounterRepository,
    settings: Settings,
) -> date:
    """Authoritatively meter a bulk import against the per-day cap, atomically.

    Re-validates the file count, then claims ``file_count`` from the per-day
    image budget in a single atomic upsert. Unlike :func:`enforce_import_quota`
    (a cheap pre-buffer read), the increment and cap check happen in one
    statement, so N concurrent imports cannot all read the same pre-increment
    count and overshoot the quota (the prior TOCTOU race). A rejected import
    consumes nothing, so it never over-counts or locks the user out.

    Returns the UTC day the import was metered against.

    Raises:
        InvalidUploadError: If *file_count* is empty or exceeds the per-request cap.
        ImportQuotaExceededError: If the per-day image quota would be exceeded.
    """
    if file_count < 1:
        raise InvalidUploadError("At least one image is required.")
    if file_count > settings.library_import_max_files:
        raise InvalidUploadError(
            f"Too many files: at most {settings.library_import_max_files} per import."
        )

    today = datetime.now(UTC).date()
    new_total = await usage_repo.increment_within_cap(
        user_id,
        _IMPORT_IMAGES_KEY,
        today,
        amount=file_count,
        cap=settings.library_import_images_per_day,
    )
    if new_total is None:
        raise ImportQuotaExceededError("Daily library-import limit reached. Try again tomorrow.")
    return today


def _verify_image_bytes(data: bytes) -> None:
    """Verify *data* is a real, decodable image; reject MIME/extension spoofing.

    A declared ``image/*`` MIME type is attacker-controlled, so confirm the
    actual bytes parse as an image (magic-byte / structural check) before any
    of them reach the vision LLM or are persisted.

    Raises:
        InvalidUploadError: If the bytes are not a valid image.
    """
    try:
        # ``register_heif_opener`` is a no-op import guard for HEIC/HEIF.
        try:
            import pillow_heif

            pillow_heif.register_heif_opener()
        except ImportError:
            pass
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
    except InvalidUploadError:
        raise
    except Exception as exc:
        # Any decode failure means the bytes are not a valid image.
        raise InvalidUploadError("File is not a valid image.") from exc


def validate_image(
    content_type: str | None,
    size_bytes: int,
    settings: Settings,
    data: bytes | None = None,
) -> None:
    """Guard a single uploaded image by MIME type, size, and (if given) magic bytes.

    Raises:
        InvalidUploadError: If the file is not an image or exceeds the size cap.
    """
    if not content_type or not content_type.startswith("image/"):
        raise InvalidUploadError("File must be an image.")
    max_size = settings.capture_max_image_mb * 1024 * 1024
    if size_bytes > max_size:
        raise InvalidUploadError(f"Image file must be under {settings.capture_max_image_mb}MB.")
    if data is not None:
        _verify_image_bytes(data)


def validate_import_image(
    content_type: str | None,
    size_bytes: int,
    settings: Settings,
    data: bytes | None = None,
) -> None:
    """Guard one image from a bulk library import (different user-facing wording)."""
    if not content_type or not content_type.startswith("image/"):
        raise InvalidUploadError("All files must be images.")
    max_size = settings.capture_max_image_mb * 1024 * 1024
    if size_bytes > max_size:
        raise InvalidUploadError(f"Each image must be under {settings.capture_max_image_mb}MB.")
    if data is not None:
        _verify_image_bytes(data)


async def read_upload_capped(
    file: UploadFile,
    max_bytes: int,
    *,
    too_large_message: str,
) -> bytes:
    """Read an ``UploadFile`` into memory, aborting once *max_bytes* is exceeded.

    Checks the declared ``size`` (from ``Content-Length``) up front and then
    reads in bounded chunks so an oversized upload is rejected before it is
    fully buffered.

    Raises:
        InvalidUploadError: If the upload exceeds *max_bytes*.
    """
    if file.size is not None and file.size > max_bytes:
        raise InvalidUploadError(too_large_message)

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_READ_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise InvalidUploadError(too_large_message)
        chunks.append(chunk)
    return b"".join(chunks)


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
