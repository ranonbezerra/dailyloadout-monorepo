"""Deterministic OCR client for tests and offline development.

Treats the image payload as UTF-8 text: each non-empty line becomes an
``OcrLine``. This lets tests feed an arbitrary number of titles (1, 40, 100)
without a real image. A leading ``__lowconf__`` marker line forces a low
``mean_confidence`` so the local -> vision fallback path can be exercised.
"""

from __future__ import annotations

from .base import AbstractOCRClient, OcrLine, OcrResult

_LOW_CONFIDENCE_MARKER = "__lowconf__"
_HIGH_CONFIDENCE = 0.95
_LOW_CONFIDENCE = 0.30


class DummyOCRClient(AbstractOCRClient):
    async def extract_lines(self, image_bytes: bytes) -> OcrResult:
        payload = image_bytes.decode("utf-8", errors="ignore")
        raw_lines = [line.strip() for line in payload.splitlines()]

        low_confidence = False
        if raw_lines and raw_lines[0] == _LOW_CONFIDENCE_MARKER:
            low_confidence = True
            raw_lines = raw_lines[1:]

        lines = [
            OcrLine(text=text, confidence=_LOW_CONFIDENCE if low_confidence else _HIGH_CONFIDENCE)
            for text in raw_lines
            if text
        ]
        mean = (
            sum(line.confidence for line in lines) / len(lines)
            if lines
            else (_LOW_CONFIDENCE if low_confidence else 0.0)
        )
        return OcrResult(lines=lines, mean_confidence=mean)
