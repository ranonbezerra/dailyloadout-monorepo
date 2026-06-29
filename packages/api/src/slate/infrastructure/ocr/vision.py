"""Cloud/vision OCR fallback for low-confidence images.

Wraps the existing LLM vision capability (``parse_capture_image``) so noisy
inputs — cover-art grids, glare, console icon walls — that the local Tesseract
path reads poorly can be escalated to the vision model. Kept behind the import
path's per-day cap so the fallback stays cheap. Reuses the Epic 5 Ollama vision
model today; a cloud vision model can slot in behind the same LLM port later
(Epic 13) with no change here.
"""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING

import structlog

from .base import AbstractOCRClient, OcrLine, OcrResult, OCRUnavailableError

if TYPE_CHECKING:
    from slate.infrastructure.llm.base import AbstractLLMClient

logger = structlog.get_logger()

# The vision model already returns a per-title confidence; treat its output as
# high-confidence lines (the model has done the recognition + cleanup itself).
_FALLBACK_CONFIDENCE = 0.9


class VisionOCRClient(AbstractOCRClient):
    def __init__(self, llm_client: AbstractLLMClient) -> None:
        self._llm_client = llm_client

    async def extract_lines(self, image_bytes: bytes) -> OcrResult:
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        try:
            extracted = await self._llm_client.parse_capture_image(image_base64)
        except Exception as exc:
            raise OCRUnavailableError(str(exc)) from exc

        lines = [
            OcrLine(text=game.title, confidence=game.confidence or _FALLBACK_CONFIDENCE)
            for game in extracted
            if game.title.strip()
        ]
        mean = sum(line.confidence for line in lines) / len(lines) if lines else 0.0
        return OcrResult(lines=lines, mean_confidence=mean)
