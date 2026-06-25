"""Stats dependencies: repository and service."""

from typing import Annotated

from fastapi import Depends

from dailyloadout.config import settings
from dailyloadout.core.stats.service import StatsService
from dailyloadout.infrastructure.cache.factory import get_cache
from dailyloadout.infrastructure.db.repositories.stats import StatsRepository

from .db import DbSession


def get_stats_repo(db: DbSession) -> StatsRepository:
    return StatsRepository(db)


StatsRepoDep = Annotated[StatsRepository, Depends(get_stats_repo)]


def get_stats_service(stats_repo: StatsRepoDep) -> StatsService:
    return StatsService(
        stats_repo,
        cache=get_cache(settings),
        ttl_seconds=settings.stats_cache_ttl_seconds,
    )


StatsServiceDep = Annotated[StatsService, Depends(get_stats_service)]
