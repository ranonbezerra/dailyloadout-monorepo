"""Bulk library-import processing (ROADMAP Epic 14).

Reads one or more library screenshots, escalating only low-confidence images to
the vision fallback (under a per-day cap), then repairs each line against the
canonical catalog and emits a batch of ``capture_candidates`` for the user to
confirm. No LLM is in the matching loop — only the optional vision OCR fallback.
"""

from __future__ import annotations

from datetime import date

import structlog

from dailyloadout.config import Settings
from dailyloadout.infrastructure.catalog.base import AbstractCatalogMatcher, CatalogMatch
from dailyloadout.infrastructure.db.models import Capture
from dailyloadout.infrastructure.db.repositories.capture import (
    CaptureCandidateRepository,
    CaptureRepository,
)
from dailyloadout.infrastructure.db.repositories.usage import UsageCounterRepository
from dailyloadout.infrastructure.ocr.base import AbstractOCRClient, OcrLine

logger = structlog.get_logger()

VISION_FALLBACK_KEY = "ocr_vision_fallback"
IMAGES_KEY = "library_import_images"

_MIN_LINE_LENGTH = 2


def _is_meaningful(text: str) -> bool:
    """Drop junk lines: too short, or with no letters (counts, prices, icons)."""
    cleaned = text.strip()
    return len(cleaned) >= _MIN_LINE_LENGTH and any(ch.isalpha() for ch in cleaned)


def _dedupe(lines: list[OcrLine], limit: int) -> list[str]:
    """Order-preserving dedupe of meaningful line texts, capped at *limit*."""
    seen: set[str] = set()
    titles: list[str] = []
    for line in lines:
        text = line.text.strip()
        if not _is_meaningful(text):
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        titles.append(text)
        if len(titles) >= limit:
            break
    return titles


def _candidate_dict(match: CatalogMatch) -> dict[str, object]:
    return {
        "title": match.title,
        "confidence": match.confidence,
        "igdb_id": match.igdb_id,
        "igdb_title": match.title if match.matched else None,
        "igdb_cover_url": match.cover_url,
        "igdb_summary": match.summary,
        "igdb_genres": match.genres,
        "igdb_first_release_date": match.first_release_date,
    }


async def process_library_import(
    capture: Capture,
    image_byte_blobs: list[bytes],
    *,
    user_id: int,
    today: date,
    capture_repo: CaptureRepository,
    candidate_repo: CaptureCandidateRepository,
    usage_repo: UsageCounterRepository,
    ocr_client: AbstractOCRClient,
    ocr_fallback_client: AbstractOCRClient | None,
    catalog_matcher: AbstractCatalogMatcher,
    settings: Settings,
) -> Capture:
    """OCR each image, fall back when needed, match titles, create candidates."""
    try:
        await capture_repo.update_status(capture.id, "processing")

        all_lines: list[OcrLine] = []
        for blob in image_byte_blobs:
            result = await ocr_client.extract_lines(blob)

            # Escalate only low-confidence images, and only within the daily cap.
            if (
                result.mean_confidence < settings.ocr_confidence_threshold
                and ocr_fallback_client is not None
            ):
                used = await usage_repo.get_count(user_id, VISION_FALLBACK_KEY, today)
                if used < settings.library_import_vision_fallbacks_per_day:
                    await usage_repo.increment(user_id, VISION_FALLBACK_KEY, today)
                    logger.info("library_import_vision_fallback", capture_id=capture.id)
                    result = await ocr_fallback_client.extract_lines(blob)

            all_lines.extend(result.lines)

        titles = _dedupe(all_lines, settings.library_import_max_candidates)
        if not titles:
            await capture_repo.update_status(
                capture.id, "review", error_message="No game titles found in the screenshots"
            )
            return capture

        matches = await catalog_matcher.match_many(titles)
        await candidate_repo.create_bulk(capture.id, [_candidate_dict(m) for m in matches])
        await capture_repo.update_status(capture.id, "review")
        logger.info("library_import_processed", capture_id=capture.id, candidates=len(matches))
    except Exception as exc:
        logger.error("library_import_failed", capture_id=capture.id, exc_info=True)
        await capture_repo.update_status(capture.id, "failed", error_message=str(exc))

    return capture
