"""Local Tesseract OCR provider with image preprocessing.

The default, zero-API-cost path: clean list-view screenshots resolve here on
VPS CPU. Preprocessing (grayscale, autocontrast, upscale, binarize) lifts
recognition on typical platform UIs. Tesseract is synchronous, so the work runs
in a thread to keep the event loop free (same discipline as Whisper in Epic 4).
"""

from __future__ import annotations

import asyncio
import io

import pytesseract
import structlog
from PIL import Image, ImageOps

from slate.core.capture import _pil_safety  # noqa: F401 - sets PIL bomb guard

from .base import AbstractOCRClient, OcrLine, OcrResult, OCRUnavailableError

logger = structlog.get_logger()

# Tesseract reports per-word confidence as 0-100 (or -1 for non-text); we drop
# anything below this to keep noise out of the catalog matcher.
_MIN_WORD_CONFIDENCE = 30.0
# Upscale small screenshots so Tesseract has enough pixels per glyph.
_MIN_WIDTH = 1000


def _preprocess(image_bytes: bytes) -> Image.Image:
    """Grayscale, normalise contrast, upscale, and binarize for OCR."""
    image: Image.Image = Image.open(io.BytesIO(image_bytes))
    image = ImageOps.exif_transpose(image)
    image = image.convert("L")
    image = ImageOps.autocontrast(image)

    if image.width < _MIN_WIDTH:
        scale = _MIN_WIDTH / image.width
        new_size = (_MIN_WIDTH, max(1, round(image.height * scale)))
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    # Simple binarization keeps text crisp against busy launcher backgrounds.
    return image.point(lambda px: 255 if px > 140 else 0, mode="1")


def _extract_sync(image_bytes: bytes) -> OcrResult:
    try:
        image = _preprocess(image_bytes)
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    except Exception as exc:  # pillow decode / tesseract binary missing, etc.
        raise OCRUnavailableError(str(exc)) from exc

    # Group words into lines by (block, paragraph, line) and average confidence.
    groups: dict[tuple[int, int, int], list[tuple[str, float, tuple[int, int, int, int]]]] = {}
    for i, raw_text in enumerate(data["text"]):
        text = raw_text.strip()
        conf = float(data["conf"][i])
        if not text or conf < _MIN_WORD_CONFIDENCE:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        bbox = (data["left"][i], data["top"][i], data["width"][i], data["height"][i])
        groups.setdefault(key, []).append((text, conf, bbox))

    lines: list[OcrLine] = []
    for key in sorted(groups):
        words = groups[key]
        text = " ".join(w[0] for w in words)
        confidence = sum(w[1] for w in words) / len(words) / 100.0
        x = min(w[2][0] for w in words)
        y = min(w[2][1] for w in words)
        right = max(w[2][0] + w[2][2] for w in words)
        bottom = max(w[2][1] + w[2][3] for w in words)
        lines.append(OcrLine(text=text, confidence=confidence, bbox=(x, y, right - x, bottom - y)))

    mean = sum(line.confidence for line in lines) / len(lines) if lines else 0.0
    return OcrResult(lines=lines, mean_confidence=mean)


class TesseractOCRClient(AbstractOCRClient):
    async def extract_lines(self, image_bytes: bytes) -> OcrResult:
        return await asyncio.to_thread(_extract_sync, image_bytes)
