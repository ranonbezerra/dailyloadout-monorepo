"""Capture processing logic: LLM extraction + optional IGDB enrichment.

This module contains the processing pipeline that:
1. Parses raw text via an LLM to extract game titles.
2. Optionally enriches each title with IGDB metadata.
3. Creates CaptureCandidate records for user review.

NOTE: Currently invoked inline from the API endpoint for simplicity.
This will move to background processing via arq once the task queue
infrastructure is fully wired.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path

import structlog
from PIL import Image

from dailyloadout.infrastructure.db.models import Capture
from dailyloadout.infrastructure.db.repositories.capture import (
    CaptureCandidateRepository,
    CaptureRepository,
)
from dailyloadout.infrastructure.igdb.base import IGDBSearchClient
from dailyloadout.infrastructure.igdb.exceptions import IGDBNotConfiguredError
from dailyloadout.infrastructure.llm.base import AbstractLLMClient

logger = structlog.get_logger()


async def process_capture(
    capture: Capture,
    capture_repo: CaptureRepository,
    candidate_repo: CaptureCandidateRepository,
    llm_client: AbstractLLMClient,
    igdb_client: IGDBSearchClient | None,
) -> Capture:
    """Process a capture: extract games via LLM and enrich with IGDB.

    Updates the capture status through its lifecycle:
    ``queued`` -> ``processing`` -> ``review`` (or ``failed``).
    """
    try:
        await capture_repo.update_status(capture.id, "processing")

        # Photo capture: read image, encode to base64, and parse via vision LLM.
        if capture.input_type == "photo":
            if not capture.image_path:
                await capture_repo.update_status(
                    capture.id, "failed", error_message="No image to process"
                )
                return capture

            image_bytes = _load_image_as_jpeg(Path(capture.image_path))
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")

            extracted = await llm_client.parse_capture_image(image_base64)
            logger.info(
                "capture_vision_extracted",
                capture_id=capture.id,
                count=len(extracted),
            )
        else:
            # Text/voice capture: parse raw text via LLM.
            if not capture.raw_text:
                await capture_repo.update_status(
                    capture.id, "failed", error_message="No text to process"
                )
                return capture

            extracted = await llm_client.parse_capture_text(capture.raw_text)
            logger.info(
                "capture_llm_extracted",
                capture_id=capture.id,
                count=len(extracted),
            )

        if not extracted:
            await capture_repo.update_status(
                capture.id, "review", error_message="No games found in text"
            )
            return capture

        # Step 2: For each extracted game, try IGDB enrichment.
        for game in extracted:
            igdb_data: dict[str, object] = {}

            if igdb_client is not None:
                try:
                    results = await igdb_client.search_games(game.title, limit=1)
                    if results:
                        best = results[0]
                        igdb_data = {
                            "igdb_id": best.igdb_id,
                            "igdb_title": best.title,
                            "igdb_cover_url": best.cover_url,
                            "igdb_summary": best.summary,
                            "igdb_genres": best.genres,
                            "igdb_first_release_date": best.first_release_date,
                        }
                except IGDBNotConfiguredError:
                    logger.info("igdb_not_configured_skipping")
                except Exception:
                    logger.warning(
                        "igdb_enrichment_failed",
                        title=game.title,
                        exc_info=True,
                    )

            await candidate_repo.create(
                capture_id=capture.id,
                title=game.title,
                platform_hint=game.platform_hint,
                confidence=game.confidence,
                **igdb_data,  # type: ignore[arg-type]
            )

        await capture_repo.update_status(capture.id, "review")

    except Exception as exc:
        logger.error(
            "capture_processing_failed",
            capture_id=capture.id,
            error=str(exc),
            exc_info=True,
        )
        await capture_repo.update_status(capture.id, "failed", error_message=str(exc))

    return capture


# Formats natively supported by Ollama's vision endpoint.
_OLLAMA_NATIVE_FORMATS = {"JPEG", "PNG", "GIF", "WEBP"}


def _load_image_as_jpeg(path: Path) -> bytes:
    """Read an image file and return JPEG bytes.

    Ollama's vision API only accepts JPEG, PNG, GIF, and WebP.  Images
    in other formats (HEIC, HEIF, BMP, TIFF, etc.) are converted to
    JPEG before being sent.
    """
    # Register HEIF/HEIC opener if available.
    try:
        import pillow_heif

        pillow_heif.register_heif_opener()
    except ImportError:
        pass

    with Image.open(path) as img:
        if img.format and img.format.upper() in _OLLAMA_NATIVE_FORMATS:
            # Already a supported format — return raw bytes as-is.
            return path.read_bytes()

        # Convert to JPEG.
        out = img.convert("RGB") if img.mode in ("RGBA", "P", "LA") else img
        buf = io.BytesIO()
        out.save(buf, format="JPEG", quality=90)
        return buf.getvalue()
