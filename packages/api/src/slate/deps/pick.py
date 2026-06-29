"""Pick dependencies: repository and service."""

from typing import Annotated

from fastapi import Depends

from slate.core.pick.service import PickService
from slate.infrastructure.db.repositories.pick import PickRepository

from .capture import LLMClientDep
from .db import DbSession
from .library import LibraryRepoDep
from .play_session import PlaySessionRepoDep

# ── Repository ────────────────────────────────────────────────────────


def get_pick_repo(db: DbSession) -> PickRepository:
    """Provide a ``PickRepository`` bound to the current session."""
    return PickRepository(db)


PickRepoDep = Annotated[PickRepository, Depends(get_pick_repo)]


# ── Service ───────────────────────────────────────────────────────────


def get_pick_service(
    pick_repo: PickRepoDep,
    library_repo: LibraryRepoDep,
    play_session_repo: PlaySessionRepoDep,
    llm_client: LLMClientDep,
) -> PickService:
    """Provide a ``PickService`` wired to the current dependencies."""
    return PickService(pick_repo, library_repo, play_session_repo, llm_client)


PickServiceDep = Annotated[PickService, Depends(get_pick_service)]
