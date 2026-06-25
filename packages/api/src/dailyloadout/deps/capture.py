"""Capture dependencies: repositories, service, LLM, IGDB, and STT clients."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from dailyloadout.config import settings
from dailyloadout.core.capture.service import CaptureService
from dailyloadout.infrastructure.cache.factory import get_cache
from dailyloadout.infrastructure.db.repositories.capture import (
    CaptureCandidateRepository,
    CaptureRepository,
)
from dailyloadout.infrastructure.igdb.base import IGDBSearchClient
from dailyloadout.infrastructure.igdb.cached import CachedIGDBClient
from dailyloadout.infrastructure.igdb.client import IGDBClient
from dailyloadout.infrastructure.igdb.exceptions import IGDBNotConfiguredError
from dailyloadout.infrastructure.llm.base import AbstractLLMClient
from dailyloadout.infrastructure.llm.factory import get_llm_client
from dailyloadout.infrastructure.stt.base import AbstractSTTClient
from dailyloadout.infrastructure.stt.factory import get_stt_client

from .db import DbSession
from .library import GameRepoDep, LibraryRepoDep, PlatformRepoDep

# ── Repositories ───────────────────────────────────────────────────────


def get_capture_repo(db: DbSession) -> CaptureRepository:
    """Provide a ``CaptureRepository`` bound to the current session."""
    return CaptureRepository(db)


def get_candidate_repo(db: DbSession) -> CaptureCandidateRepository:
    """Provide a ``CaptureCandidateRepository`` bound to the current session."""
    return CaptureCandidateRepository(db)


CaptureRepoDep = Annotated[CaptureRepository, Depends(get_capture_repo)]
CaptureCandidateRepoDep = Annotated[CaptureCandidateRepository, Depends(get_candidate_repo)]


# ── Infrastructure clients ─────────────────────────────────────────────


def get_llm_client_dep() -> AbstractLLMClient:
    """Provide the LLM client for the current environment."""
    return get_llm_client(settings)


# Singleton: built once so the Twitch OAuth token is reused across requests
# (rather than re-authenticating per request), and wrapped with the result cache.
_igdb_client: IGDBSearchClient | None = None
_igdb_initialized = False


def get_igdb_client_dep() -> IGDBSearchClient | None:
    """Provide the cached IGDB client (singleton), or ``None`` if unconfigured."""
    global _igdb_client, _igdb_initialized
    if not _igdb_initialized:
        try:
            base = IGDBClient(settings)
            _igdb_client = CachedIGDBClient(
                base, get_cache(settings), settings.igdb_cache_ttl_seconds
            )
        except IGDBNotConfiguredError:
            _igdb_client = None
        _igdb_initialized = True
    return _igdb_client


def get_stt_client_dep() -> AbstractSTTClient | None:
    """Provide the STT client, or ``None`` if the provider is not configured."""
    try:
        return get_stt_client(settings)
    except Exception:
        return None


LLMClientDep = Annotated[AbstractLLMClient, Depends(get_llm_client_dep)]
IGDBClientDep = Annotated[IGDBSearchClient | None, Depends(get_igdb_client_dep)]
STTClientDep = Annotated[AbstractSTTClient | None, Depends(get_stt_client_dep)]


# ── Service ────────────────────────────────────────────────────────────


def get_capture_service(
    capture_repo: CaptureRepoDep,
    candidate_repo: CaptureCandidateRepoDep,
    game_repo: GameRepoDep,
    library_repo: LibraryRepoDep,
    platform_repo: PlatformRepoDep,
) -> CaptureService:
    """Provide a ``CaptureService`` wired to the current repositories."""
    return CaptureService(capture_repo, candidate_repo, game_repo, library_repo, platform_repo)


CaptureServiceDep = Annotated[CaptureService, Depends(get_capture_service)]
