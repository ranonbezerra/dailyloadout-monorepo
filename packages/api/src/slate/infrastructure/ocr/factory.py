"""Factory for OCR clients, selected by ``OCR_PROVIDER`` / ``OCR_FALLBACK_PROVIDER``.

Defaults to the deterministic dummy under tests so no Tesseract binary or vision
model is needed in CI; production uses local Tesseract with an optional vision
fallback for low-confidence images.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from slate.config import Settings

from .base import AbstractOCRClient

if TYPE_CHECKING:
    from slate.infrastructure.llm.base import AbstractLLMClient


def get_ocr_client(settings: Settings) -> AbstractOCRClient:
    """Return the primary OCR client for the configured provider."""
    if settings.app_env == "testing" or settings.ocr_provider == "dummy":
        from .dummy import DummyOCRClient

        return DummyOCRClient()

    if settings.ocr_provider == "tesseract":
        from .tesseract import TesseractOCRClient

        return TesseractOCRClient()

    msg = f"Unknown OCR provider: {settings.ocr_provider}"
    raise ValueError(msg)


def get_ocr_fallback_client(
    settings: Settings, llm_client: AbstractLLMClient
) -> AbstractOCRClient | None:
    """Return the low-confidence fallback OCR client, or ``None`` if disabled.

    The fallback is never used under tests by default (``OCR_FALLBACK_PROVIDER``
    defaults effectively to none there); unit tests inject their own fallback.
    """
    if settings.app_env == "testing" or settings.ocr_fallback_provider == "none":
        return None

    if settings.ocr_fallback_provider == "vision":
        from .vision import VisionOCRClient

        return VisionOCRClient(llm_client)

    msg = f"Unknown OCR fallback provider: {settings.ocr_fallback_provider}"
    raise ValueError(msg)
