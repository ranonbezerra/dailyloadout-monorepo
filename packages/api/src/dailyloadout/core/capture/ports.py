"""Typed ports for the worker pipelines the capture service orchestrates.

The service calls the worker functions (``process_capture`` /
``process_library_import``) without importing them directly, keeping the
core layer decoupled from ``workers``. These Protocols describe their call
signatures so the service stays free of ``Any``.
"""

from __future__ import annotations

from datetime import date
from typing import Protocol

from dailyloadout.config import Settings
from dailyloadout.infrastructure.catalog.base import AbstractCatalogMatcher
from dailyloadout.infrastructure.db.models import Capture
from dailyloadout.infrastructure.db.repositories.capture import (
    CaptureCandidateRepository,
    CaptureRepository,
)
from dailyloadout.infrastructure.db.repositories.usage import UsageCounterRepository
from dailyloadout.infrastructure.igdb.base import IGDBSearchClient
from dailyloadout.infrastructure.llm.base import AbstractLLMClient
from dailyloadout.infrastructure.ocr.base import AbstractOCRClient


class CaptureProcessor(Protocol):
    """Call signature of ``workers.capture_processor.process_capture``."""

    async def __call__(
        self,
        capture: Capture,
        capture_repo: CaptureRepository,
        candidate_repo: CaptureCandidateRepository,
        llm_client: AbstractLLMClient,
        igdb_client: IGDBSearchClient | None,
    ) -> Capture: ...


class LibraryImportProcessor(Protocol):
    """Call signature of ``workers.library_import_processor.process_library_import``."""

    async def __call__(
        self,
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
    ) -> Capture: ...
