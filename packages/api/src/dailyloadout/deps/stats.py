"""Stats dependencies: repository and service."""

from typing import Annotated

from fastapi import Depends

from dailyloadout.core.stats.service import StatsService
from dailyloadout.infrastructure.db.repositories.stats import StatsRepository

from .db import DbSession


def get_stats_repo(db: DbSession) -> StatsRepository:
    return StatsRepository(db)


StatsRepoDep = Annotated[StatsRepository, Depends(get_stats_repo)]


def get_stats_service(stats_repo: StatsRepoDep) -> StatsService:
    return StatsService(stats_repo)


StatsServiceDep = Annotated[StatsService, Depends(get_stats_service)]
