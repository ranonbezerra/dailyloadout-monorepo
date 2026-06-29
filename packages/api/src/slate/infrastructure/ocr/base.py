"""Base classes for the OCR port (ROADMAP Epic 14 — Frictionless Library Import).

An OCR client turns a library screenshot into text lines. The local Tesseract
provider handles clean list-view text at zero API cost; a cloud/vision provider
is the low-confidence fallback. The ``mean_confidence`` on the result is the
signal the import path uses to decide whether to escalate to the fallback.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class OCRUnavailableError(RuntimeError):
    """Raised when the OCR backend cannot process the image."""


@dataclass
class OcrLine:
    """A single recognised line of text."""

    text: str
    confidence: float  # 0.0 - 1.0
    bbox: tuple[int, int, int, int] | None = None  # (x, y, width, height)


@dataclass
class OcrResult:
    """The outcome of reading one image: its lines and an overall confidence."""

    lines: list[OcrLine]
    mean_confidence: float  # 0.0 - 1.0, drives the local -> fallback escalation


class AbstractOCRClient(ABC):
    """Contract for OCR providers (local Tesseract, cloud vision, dummy)."""

    @abstractmethod
    async def extract_lines(self, image_bytes: bytes) -> OcrResult:
        """Read *image_bytes* and return recognised lines with confidences."""
        ...
