"""OCR port: image -> text lines (ROADMAP Epic 14)."""

from .base import AbstractOCRClient, OcrLine, OcrResult, OCRUnavailableError
from .factory import get_ocr_client, get_ocr_fallback_client

__all__ = [
    "AbstractOCRClient",
    "OCRUnavailableError",
    "OcrLine",
    "OcrResult",
    "get_ocr_client",
    "get_ocr_fallback_client",
]
