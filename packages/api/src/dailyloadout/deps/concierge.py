"""Backlog Concierge dependencies: agent + service."""

from typing import Annotated

from fastapi import Depends

from dailyloadout.config import settings
from dailyloadout.core.concierge.service import ConciergeService
from dailyloadout.infrastructure.agent.concierge.factory import get_concierge_agent

from .capture import LLMClientDep
from .library import LibraryRepoDep
from .mission import BriefingAgentDep, MissionRepoDep
from .stats import StatsServiceDep


def get_concierge_service(
    library_repo: LibraryRepoDep,
    mission_repo: MissionRepoDep,
    stats_service: StatsServiceDep,
    llm_client: LLMClientDep,
    briefing_agent: BriefingAgentDep,
) -> ConciergeService:
    """Provide a ``ConciergeService`` wired to the configured agent provider."""
    return ConciergeService(
        library_repo=library_repo,
        mission_repo=mission_repo,
        stats_service=stats_service,
        agent=get_concierge_agent(settings),
        llm_client=llm_client,
        briefing_agent=briefing_agent,
        settings=settings,
    )


ConciergeServiceDep = Annotated[ConciergeService, Depends(get_concierge_service)]
