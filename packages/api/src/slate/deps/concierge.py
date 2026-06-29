"""Backlog Concierge dependencies: agent + service."""

from typing import Annotated

from fastapi import Depends

from slate.config import settings
from slate.core.concierge.service import ConciergeService
from slate.infrastructure.agent.concierge.factory import get_concierge_agent

from .capture import LLMClientDep
from .library import LibraryRepoDep
from .play_session import PlaySessionRepoDep, RecapAgentDep
from .stats import StatsServiceDep


def get_concierge_service(
    library_repo: LibraryRepoDep,
    play_session_repo: PlaySessionRepoDep,
    stats_service: StatsServiceDep,
    llm_client: LLMClientDep,
    recap_agent: RecapAgentDep,
) -> ConciergeService:
    """Provide a ``ConciergeService`` wired to the configured agent provider."""
    return ConciergeService(
        library_repo=library_repo,
        play_session_repo=play_session_repo,
        stats_service=stats_service,
        agent=get_concierge_agent(settings),
        llm_client=llm_client,
        recap_agent=recap_agent,
        settings=settings,
    )


ConciergeServiceDep = Annotated[ConciergeService, Depends(get_concierge_service)]
