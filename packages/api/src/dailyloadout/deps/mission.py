"""Mission dependencies: repository and service."""

from typing import Annotated

from fastapi import Depends

from dailyloadout.core.mission.service import MissionService
from dailyloadout.infrastructure.db.repositories.mission import MissionRepository

from .capture import LLMClientDep
from .db import DbSession
from .library import LibraryRepoDep

# ── Repository ────────────────────────────────────────────────────────


def get_mission_repo(db: DbSession) -> MissionRepository:
    """Provide a ``MissionRepository`` bound to the current session."""
    return MissionRepository(db)


MissionRepoDep = Annotated[MissionRepository, Depends(get_mission_repo)]


# ── Service ───────────────────────────────────────────────────────────


def get_mission_service(
    mission_repo: MissionRepoDep,
    library_repo: LibraryRepoDep,
    llm_client: LLMClientDep,
) -> MissionService:
    """Provide a ``MissionService`` wired to the current dependencies."""
    return MissionService(mission_repo, library_repo, llm_client)


MissionServiceDep = Annotated[MissionService, Depends(get_mission_service)]
