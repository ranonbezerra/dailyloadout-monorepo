"""Loadout dependencies: repository and service."""

from typing import Annotated

from fastapi import Depends

from dailyloadout.core.loadout.service import LoadoutService
from dailyloadout.infrastructure.db.repositories.loadout import LoadoutRepository

from .capture import LLMClientDep
from .db import DbSession
from .library import LibraryRepoDep
from .mission import MissionRepoDep

# ── Repository ────────────────────────────────────────────────────────


def get_loadout_repo(db: DbSession) -> LoadoutRepository:
    """Provide a ``LoadoutRepository`` bound to the current session."""
    return LoadoutRepository(db)


LoadoutRepoDep = Annotated[LoadoutRepository, Depends(get_loadout_repo)]


# ── Service ───────────────────────────────────────────────────────────


def get_loadout_service(
    loadout_repo: LoadoutRepoDep,
    library_repo: LibraryRepoDep,
    mission_repo: MissionRepoDep,
    llm_client: LLMClientDep,
) -> LoadoutService:
    """Provide a ``LoadoutService`` wired to the current dependencies."""
    return LoadoutService(loadout_repo, library_repo, mission_repo, llm_client)


LoadoutServiceDep = Annotated[LoadoutService, Depends(get_loadout_service)]
