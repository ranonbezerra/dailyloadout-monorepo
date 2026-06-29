"""Loadout dependencies: repository and service."""

from typing import Annotated

from fastapi import Depends

from slate.core.loadout.service import LoadoutService
from slate.infrastructure.db.repositories.loadout import LoadoutRepository

from .capture import LLMClientDep
from .db import DbSession
from .library import LibraryRepoDep
from .play_session import PlaySessionRepoDep

# ── Repository ────────────────────────────────────────────────────────


def get_loadout_repo(db: DbSession) -> LoadoutRepository:
    """Provide a ``LoadoutRepository`` bound to the current session."""
    return LoadoutRepository(db)


LoadoutRepoDep = Annotated[LoadoutRepository, Depends(get_loadout_repo)]


# ── Service ───────────────────────────────────────────────────────────


def get_loadout_service(
    loadout_repo: LoadoutRepoDep,
    library_repo: LibraryRepoDep,
    play_session_repo: PlaySessionRepoDep,
    llm_client: LLMClientDep,
) -> LoadoutService:
    """Provide a ``LoadoutService`` wired to the current dependencies."""
    return LoadoutService(loadout_repo, library_repo, play_session_repo, llm_client)


LoadoutServiceDep = Annotated[LoadoutService, Depends(get_loadout_service)]
