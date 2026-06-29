"""Dependencies for the library-import path: OCR, catalog matcher, usage counters."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from slate.config import settings
from slate.core.capture.service import CaptureService
from slate.infrastructure.catalog.base import AbstractCatalogMatcher
from slate.infrastructure.catalog.factory import get_catalog_matcher
from slate.infrastructure.db.repositories.usage import UsageCounterRepository
from slate.infrastructure.ocr.base import AbstractOCRClient
from slate.infrastructure.ocr.factory import get_ocr_client, get_ocr_fallback_client
from slate.workers.capture_processor import process_capture
from slate.workers.library_import_processor import process_library_import

from .capture import (
    CaptureCandidateRepoDep,
    CaptureRepoDep,
    IGDBClientDep,
    LLMClientDep,
)
from .db import DbSession
from .library import GameRepoDep, LibraryRepoDep, PlatformRepoDep


def get_ocr_client_dep() -> AbstractOCRClient:
    """Provide the primary OCR client for the current environment."""
    return get_ocr_client(settings)


def get_ocr_fallback_client_dep(llm_client: LLMClientDep) -> AbstractOCRClient | None:
    """Provide the low-confidence vision fallback, or ``None`` if disabled."""
    return get_ocr_fallback_client(settings, llm_client)


def get_catalog_matcher_dep(igdb_client: IGDBClientDep) -> AbstractCatalogMatcher:
    """Provide the catalog matcher (dummy under tests / without IGDB)."""
    return get_catalog_matcher(settings, igdb_client)


def get_usage_repo(db: DbSession) -> UsageCounterRepository:
    """Provide a ``UsageCounterRepository`` bound to the current session."""
    return UsageCounterRepository(db)


OCRClientDep = Annotated[AbstractOCRClient, Depends(get_ocr_client_dep)]
OCRFallbackClientDep = Annotated[AbstractOCRClient | None, Depends(get_ocr_fallback_client_dep)]
CatalogMatcherDep = Annotated[AbstractCatalogMatcher, Depends(get_catalog_matcher_dep)]
UsageRepoDep = Annotated[UsageCounterRepository, Depends(get_usage_repo)]


# ── Capture service ────────────────────────────────────────────────────
#
# Wired here (not in ``deps/capture.py``) because the service now also takes the
# OCR/catalog/usage collaborators; ``deps/ocr.py`` already depends on
# ``deps/capture.py``, so this keeps the import graph acyclic.


def get_capture_service(
    capture_repo: CaptureRepoDep,
    candidate_repo: CaptureCandidateRepoDep,
    game_repo: GameRepoDep,
    library_repo: LibraryRepoDep,
    platform_repo: PlatformRepoDep,
    llm_client: LLMClientDep,
    igdb_client: IGDBClientDep,
    usage_repo: UsageRepoDep,
    ocr_client: OCRClientDep,
    ocr_fallback_client: OCRFallbackClientDep,
    catalog_matcher: CatalogMatcherDep,
) -> CaptureService:
    """Provide a ``CaptureService`` wired to repositories, clients, and pipelines.

    The ingestion collaborators (LLM/IGDB/OCR, usage repo, catalog matcher) and
    the worker functions are injected so the routers only parse + delegate.
    """
    return CaptureService(
        capture_repo,
        candidate_repo,
        game_repo,
        library_repo,
        platform_repo,
        usage_repo=usage_repo,
        llm_client=llm_client,
        igdb_client=igdb_client,
        ocr_client=ocr_client,
        ocr_fallback_client=ocr_fallback_client,
        catalog_matcher=catalog_matcher,
        process_capture=process_capture,
        process_library_import=process_library_import,
        settings=settings,
    )


CaptureServiceDep = Annotated[CaptureService, Depends(get_capture_service)]
