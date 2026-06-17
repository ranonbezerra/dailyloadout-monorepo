"""Library dependencies: repositories and service."""

from typing import Annotated

from fastapi import Depends

from dailyloadout.core.library.service import LibraryService
from dailyloadout.infrastructure.db.repositories.game import GameRepository
from dailyloadout.infrastructure.db.repositories.library import LibraryRepository
from dailyloadout.infrastructure.db.repositories.platform import PlatformRepository

from .db import DbSession

# ── Repositories ───────────────────────────────────────────────────────


def get_game_repo(db: DbSession) -> GameRepository:
    """Provide a ``GameRepository`` bound to the current session."""
    return GameRepository(db)


def get_library_repo(db: DbSession) -> LibraryRepository:
    """Provide a ``LibraryRepository`` bound to the current session."""
    return LibraryRepository(db)


def get_platform_repo(db: DbSession) -> PlatformRepository:
    """Provide a ``PlatformRepository`` bound to the current session."""
    return PlatformRepository(db)


GameRepoDep = Annotated[GameRepository, Depends(get_game_repo)]
LibraryRepoDep = Annotated[LibraryRepository, Depends(get_library_repo)]
PlatformRepoDep = Annotated[PlatformRepository, Depends(get_platform_repo)]


# ── Service ────────────────────────────────────────────────────────────


def get_library_service(
    game_repo: GameRepoDep,
    library_repo: LibraryRepoDep,
    platform_repo: PlatformRepoDep,
) -> LibraryService:
    """Provide a ``LibraryService`` wired to the current repositories."""
    return LibraryService(game_repo, library_repo, platform_repo)


LibraryServiceDep = Annotated[LibraryService, Depends(get_library_service)]
