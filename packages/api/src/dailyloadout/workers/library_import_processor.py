"""Bulk library-import processing (ROADMAP Epic 14).

Reads one or more library screenshots, escalating only low-confidence images to
the vision fallback (under a per-day cap), then repairs each line against the
canonical catalog and emits a batch of ``capture_candidates`` for the user to
confirm. No LLM is in the matching loop — only the optional vision OCR fallback.
"""

from __future__ import annotations

import re
from datetime import date

import structlog

from dailyloadout.config import Settings
from dailyloadout.core.library.igdb_budget import igdb_budget_allows
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

# Strip leading/trailing symbol noise — list rows often have a platform/launcher
# icon to the left of the title that OCR misreads as a stray glyph (e.g. "▶",
# "•", "©") or a lone separator. Keeps inner punctuation (S.T.A.L.K.E.R.).
_EDGE_NOISE = re.compile(r"^[^0-9A-Za-z]+|[^0-9A-Za-z]+$")
# A lone leading single character followed by a space is almost always an icon
# artifact, not part of the title (real one-letter prefixes are rare and the
# user can edit). Only strip when what's left still has real words.
_LEADING_GLYPH = re.compile(r"^\S\s+(?=\S)")


def _clean_title(text: str) -> str:
    """Remove leading/trailing icon/symbol noise from an OCR line."""
    cleaned = _EDGE_NOISE.sub("", text).strip()
    stripped = _LEADING_GLYPH.sub("", cleaned).strip()
    # Don't let aggressive stripping erase the whole title.
    return stripped if len(stripped) >= _MIN_LINE_LENGTH else cleaned


def _is_meaningful(text: str) -> bool:
    """Drop junk lines: too short, or with no letters (counts, prices, icons)."""
    cleaned = text.strip()
    return len(cleaned) >= _MIN_LINE_LENGTH and any(ch.isalpha() for ch in cleaned)


def _dedupe(lines: list[OcrLine], limit: int) -> list[str]:
    """Clean, filter, and order-preserving-dedupe line texts, capped at *limit*."""
    seen: set[str] = set()
    titles: list[str] = []
    for line in lines:
        text = _clean_title(line.text)
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


async def _match_within_igdb_budget(
    matcher: AbstractCatalogMatcher, titles: list[str], user_id: int
) -> list[CatalogMatch]:
    """Match *titles*, debiting each live IGDB search against the user's budget.

    Each matched title fans out to one outbound IGDB search; without this, a
    bulk import (up to ``library_import_max_candidates`` novel titles per call)
    bypassed the per-user/day IGDB budget the single-capture and create-game
    paths already enforce, letting one account drain the app-wide IGDB quota.
    Once the budget is spent, remaining titles resolve LOCAL-ONLY (``matched=
    False``) instead of firing more outbound calls — the same degraded behaviour
    the single-capture path uses.
    """
    matches: list[CatalogMatch] = []
    budget_spent = False
    for title in titles:
        if budget_spent or not await igdb_budget_allows(user_id):
            budget_spent = True
            matches.append(
                CatalogMatch(line_text=title, matched=False, confidence=0.0, title=title)
            )
            continue
        matches.append(await matcher.match(title))
    return matches


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
                # Atomically claim a vision-fallback slot: increments only when
                # the new total stays within the daily cap, so concurrent tasks
                # for the same user can't both pass the check and overshoot.
                claimed = await usage_repo.increment_within_cap(
                    user_id,
                    VISION_FALLBACK_KEY,
                    today,
                    amount=1,
                    cap=settings.library_import_vision_fallbacks_per_day,
                )
                if claimed is not None:
                    logger.info("library_import_vision_fallback", capture_id=capture.id)
                    result = await ocr_fallback_client.extract_lines(blob)

            all_lines.extend(result.lines)

        titles = _dedupe(all_lines, settings.library_import_max_candidates)
        if not titles:
            await capture_repo.update_status(
                capture.id, "review", error_message="No game titles found in the screenshots"
            )
            return capture

        matches = await _match_within_igdb_budget(catalog_matcher, titles, user_id)
        await candidate_repo.create_bulk(capture.id, [_candidate_dict(m) for m in matches])
        await capture_repo.update_status(capture.id, "review")
        logger.info("library_import_processed", capture_id=capture.id, candidates=len(matches))
    except Exception:
        # Persist a generic, user-facing message. The full exception (with its
        # traceback) is logged server-side; raw internals must never reach the
        # client via the capture's error_message.
        logger.error("library_import_failed", capture_id=capture.id, exc_info=True)
        await capture_repo.update_status(
            capture.id, "failed", error_message="Import failed. Please try again."
        )

    return capture
