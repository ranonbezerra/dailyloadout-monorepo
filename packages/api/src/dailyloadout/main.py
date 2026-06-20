import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from scalar_fastapi import get_scalar_api_reference
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from dailyloadout.api.v1.auth import limiter
from dailyloadout.api.v1.auth import router as auth_router
from dailyloadout.api.v1.capture import router as capture_router
from dailyloadout.api.v1.library import router as library_router
from dailyloadout.api.v1.loadout import router as loadout_router
from dailyloadout.api.v1.mission import router as mission_router
from dailyloadout.config import settings

logger = structlog.get_logger()

AUTO_CLAMP_INTERVAL_SECONDS = 3600  # 1 hour
AUTO_IGNORE_INTERVAL_SECONDS = 3600  # 1 hour


async def _ensure_single_user() -> None:
    """Create the default single-user account if it does not exist yet."""
    from sqlalchemy import select

    from dailyloadout.infrastructure.db.models import User
    from dailyloadout.infrastructure.db.session import async_session_factory

    async with async_session_factory() as session:
        stmt = select(User).where(User.email == settings.single_user_email)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is None:
            user = User(
                email=settings.single_user_email,
                password_hash=None,
                display_name="Player One",
            )
            session.add(user)
            await session.commit()
            logger.info(
                "single_user_created",
                email=settings.single_user_email,
            )
        else:
            logger.info(
                "single_user_exists",
                email=settings.single_user_email,
            )


async def _auto_clamp_loop() -> None:
    """Periodically close stale missions that exceed the configured timeout."""
    from dailyloadout.infrastructure.db.repositories.mission import MissionRepository
    from dailyloadout.infrastructure.db.session import async_session_factory
    from dailyloadout.workers.mission_auto_clamp import auto_clamp_stale_missions

    while True:
        await asyncio.sleep(AUTO_CLAMP_INTERVAL_SECONDS)
        try:
            async with async_session_factory() as session:
                repo = MissionRepository(session)
                clamped = await auto_clamp_stale_missions(
                    repo, max_hours=settings.mission_auto_clamp_hours
                )
                await session.commit()
                if clamped:
                    logger.info("auto_clamp_cycle_done", clamped=clamped)
        except Exception:
            logger.exception("auto_clamp_cycle_error")


async def _auto_ignore_loop() -> None:
    """Periodically mark stale loadouts as ignored."""
    from dailyloadout.infrastructure.db.repositories.loadout import LoadoutRepository
    from dailyloadout.infrastructure.db.session import async_session_factory
    from dailyloadout.workers.loadout_auto_ignore import auto_ignore_stale_loadouts

    while True:
        await asyncio.sleep(AUTO_IGNORE_INTERVAL_SECONDS)
        try:
            async with async_session_factory() as session:
                repo = LoadoutRepository(session)
                ignored = await auto_ignore_stale_loadouts(repo, max_hours=24)
                await session.commit()
                if ignored:
                    logger.info("auto_ignore_cycle_done", ignored=ignored)
        except Exception:
            logger.exception("auto_ignore_cycle_error")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Single-user mode: ensure the default account exists.
    if settings.single_user_mode:
        await _ensure_single_user()

    # Start periodic background tasks.
    clamp_task = asyncio.create_task(_auto_clamp_loop())
    ignore_task = asyncio.create_task(_auto_ignore_loop())

    yield

    clamp_task.cancel()
    ignore_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await clamp_task
    with contextlib.suppress(asyncio.CancelledError):
        await ignore_task


def create_app() -> FastAPI:
    application = FastAPI(
        title="DailyLoadout API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
    )

    # CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiting
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    # Routers
    application.include_router(auth_router)
    application.include_router(capture_router)
    application.include_router(library_router)
    application.include_router(mission_router)
    application.include_router(loadout_router)

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/docs", include_in_schema=False)
    async def scalar_docs() -> HTMLResponse:
        return get_scalar_api_reference(
            openapi_url=application.openapi_url or "/openapi.json",
            title=application.title,
        )

    return application


app = create_app()
