"""Mission dependencies: repository and service."""

from typing import Annotated

from fastapi import Depends

from dailyloadout.config import settings
from dailyloadout.core.mission.service import MissionService
from dailyloadout.infrastructure.agent.base import AbstractBriefingAgent
from dailyloadout.infrastructure.agent.factory import get_briefing_agent
from dailyloadout.infrastructure.cache.factory import get_cache
from dailyloadout.infrastructure.db.repositories.mission import MissionRepository

from .capture import LLMClientDep
from .db import DbSession
from .library import LibraryRepoDep

# ── Repository ────────────────────────────────────────────────────────


def get_mission_repo(db: DbSession) -> MissionRepository:
    """Provide a ``MissionRepository`` bound to the current session."""
    return MissionRepository(db)


MissionRepoDep = Annotated[MissionRepository, Depends(get_mission_repo)]


# ── Briefing agent ────────────────────────────────────────────────────


def get_briefing_agent_dep(llm_client: LLMClientDep) -> AbstractBriefingAgent | None:
    """Provide the deep-research briefing agent, or ``None`` if disabled."""
    return get_briefing_agent(settings, llm_client)


BriefingAgentDep = Annotated[AbstractBriefingAgent | None, Depends(get_briefing_agent_dep)]


# ── Service ───────────────────────────────────────────────────────────


def get_mission_service(
    mission_repo: MissionRepoDep,
    library_repo: LibraryRepoDep,
    llm_client: LLMClientDep,
    agent: BriefingAgentDep,
) -> MissionService:
    """Provide a ``MissionService`` wired to the current dependencies."""
    return MissionService(
        mission_repo,
        library_repo,
        llm_client,
        agent=agent,
        settings=settings,
        cache=get_cache(settings),
    )


MissionServiceDep = Annotated[MissionService, Depends(get_mission_service)]
