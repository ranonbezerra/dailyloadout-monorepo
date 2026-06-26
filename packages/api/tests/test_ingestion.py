"""Unit tests for upload ingestion guards: size caps, magic bytes, capped read."""

from __future__ import annotations

import io

import pytest
from fastapi import UploadFile
from PIL import Image

from dailyloadout.config import settings
from dailyloadout.core.capture.exceptions import InvalidUploadError
from dailyloadout.core.capture.ingestion import (
    read_upload_capped,
    validate_image,
    validate_import_image,
)


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (1, 1), (0, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


def test_validate_image_rejects_oversized() -> None:
    too_big = settings.capture_max_image_mb * 1024 * 1024 + 1
    with pytest.raises(InvalidUploadError, match="under"):
        validate_image("image/png", too_big, settings)


def test_validate_image_accepts_real_png() -> None:
    data = _png()
    validate_image("image/png", len(data), settings, data=data)  # no raise


def test_validate_image_rejects_spoofed_bytes() -> None:
    with pytest.raises(InvalidUploadError, match="valid image"):
        validate_image("image/png", 10, settings, data=b"not an image")


def test_validate_import_image_rejects_oversized() -> None:
    too_big = settings.capture_max_image_mb * 1024 * 1024 + 1
    with pytest.raises(InvalidUploadError, match="under"):
        validate_import_image("image/png", too_big, settings)


def test_validate_import_image_rejects_spoofed_bytes() -> None:
    with pytest.raises(InvalidUploadError, match="valid image"):
        validate_import_image("image/png", 5, settings, data=b"plain text")


async def test_read_upload_capped_rejects_declared_oversize() -> None:
    big = b"x" * 100
    upload = UploadFile(filename="f", file=io.BytesIO(big), size=100)
    with pytest.raises(InvalidUploadError, match="too big"):
        await read_upload_capped(upload, 10, too_large_message="too big")


async def test_read_upload_capped_rejects_streamed_oversize() -> None:
    # No declared size, so the cap is enforced while reading chunks.
    upload = UploadFile(filename="f", file=io.BytesIO(b"x" * 100))
    upload.size = None  # force the streaming path
    with pytest.raises(InvalidUploadError, match="too big"):
        await read_upload_capped(upload, 10, too_large_message="too big")


async def test_read_upload_capped_returns_small_payload() -> None:
    upload = UploadFile(filename="f", file=io.BytesIO(b"hello"), size=5)
    data = await read_upload_capped(upload, 1000, too_large_message="too big")
    assert data == b"hello"
