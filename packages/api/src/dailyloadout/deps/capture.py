"""Capture dependencies: repositories, service, LLM, IGDB, and STT clients."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from dailyloadout.config import settings
from dailyloadout.core.capture.service import CaptureService
from dailyloadout.infrastructure.db.repositories.capture import (
    CaptureCandidateRepository,
    CaptureRepository,
)
from dailyloadout.infrastructure.igdb.client import IGDBClient
from dailyloadout.infrastructure.igdb.exceptions import IGDBNotConfigured
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


def get_igdb_client_dep() -> IGDBClient | None:
    """Provide the IGDB client, or ``None`` if credentials are missing."""
    try:
        return IGDBClient(settings)
    except IGDBNotConfigured:
        return None


def get_stt_client_dep() -> AbstractSTTClient | None:
    """Provide the STT client, or ``None`` if the provider is not configured."""
    try:
        return get_stt_client(settings)
    except Exception:
        return None


LLMClientDep = Annotated[AbstractLLMClient, Depends(get_llm_client_dep)]
IGDBClientDep = Annotated[IGDBClient | None, Depends(get_igdb_client_dep)]
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
