"""PlaySession dependencies: repository and service."""

from typing import Annotated

from fastapi import Depends

from slate.config import settings
from slate.core.play_session.service import PlaySessionService
from slate.infrastructure.agent.base import AbstractRecapAgent
from slate.infrastructure.agent.factory import get_recap_agent
from slate.infrastructure.db.repositories.play_session import PlaySessionRepository

from .capture import LLMClientDep
from .db import DbSession
from .library import LibraryRepoDep

# ── Repository ────────────────────────────────────────────────────────


def get_play_session_repo(db: DbSession) -> PlaySessionRepository:
    """Provide a ``PlaySessionRepository`` bound to the current session."""
    return PlaySessionRepository(db)


PlaySessionRepoDep = Annotated[PlaySessionRepository, Depends(get_play_session_repo)]


# ── Recap agent ────────────────────────────────────────────────────


def get_recap_agent_dep(llm_client: LLMClientDep) -> AbstractRecapAgent | None:
    """Provide the deep-research recap agent, or ``None`` if disabled."""
    return get_recap_agent(settings, llm_client)


RecapAgentDep = Annotated[AbstractRecapAgent | None, Depends(get_recap_agent_dep)]


# ── Service ───────────────────────────────────────────────────────────


def get_play_session_service(
    play_session_repo: PlaySessionRepoDep,
    library_repo: LibraryRepoDep,
    llm_client: LLMClientDep,
    agent: RecapAgentDep,
) -> PlaySessionService:
    """Provide a ``PlaySessionService`` wired to the current dependencies."""
    return PlaySessionService(
        play_session_repo,
        library_repo,
        llm_client,
        agent=agent,
        settings=settings,
    )


PlaySessionServiceDep = Annotated[PlaySessionService, Depends(get_play_session_service)]
