"""Library dependencies: repositories and service."""

from typing import Annotated

from fastapi import Depends

from slate.config import settings
from slate.core.library.service import LibraryService
from slate.infrastructure.cache.factory import get_cache
from slate.infrastructure.config.dynamic import dynamic_config
from slate.infrastructure.db.repositories.game import GameRepository
from slate.infrastructure.db.repositories.library import LibraryRepository
from slate.infrastructure.db.repositories.platform import PlatformRepository

from .capture import IGDBClientDep
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


async def get_library_service(
    game_repo: GameRepoDep,
    library_repo: LibraryRepoDep,
    platform_repo: PlatformRepoDep,
    igdb_client: IGDBClientDep,
) -> LibraryService:
    """Provide a ``LibraryService`` wired to the current repositories.

    ``share_threshold`` is read from the dynamic overlay so it can be adjusted
    live (curating the shared catalogue is a product knob, not a redeploy).
    """
    return LibraryService(
        game_repo,
        library_repo,
        platform_repo,
        cache=get_cache(settings),
        reference_ttl_seconds=settings.reference_cache_ttl_seconds,
        reference_process_ttl_seconds=settings.reference_process_ttl_seconds,
        igdb_client=igdb_client,
        match_min_score=settings.catalog_match_min_score,
        share_threshold=await dynamic_config.get_int("catalog_share_threshold"),
    )


LibraryServiceDep = Annotated[LibraryService, Depends(get_library_service)]
