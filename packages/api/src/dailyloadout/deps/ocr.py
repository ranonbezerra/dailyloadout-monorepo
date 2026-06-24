"""Dependencies for the library-import path: OCR, catalog matcher, usage counters."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from dailyloadout.config import settings
from dailyloadout.infrastructure.catalog.base import AbstractCatalogMatcher
from dailyloadout.infrastructure.catalog.factory import get_catalog_matcher
from dailyloadout.infrastructure.db.repositories.usage import UsageCounterRepository
from dailyloadout.infrastructure.ocr.base import AbstractOCRClient
from dailyloadout.infrastructure.ocr.factory import get_ocr_client, get_ocr_fallback_client

from .capture import IGDBClientDep, LLMClientDep
from .db import DbSession


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
