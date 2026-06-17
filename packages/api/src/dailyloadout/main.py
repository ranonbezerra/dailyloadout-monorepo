from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from scalar_fastapi import get_scalar_api_reference
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from dailyloadout.api.v1.auth import limiter
from dailyloadout.api.v1.auth import router as auth_router
from dailyloadout.config import settings

logger = structlog.get_logger()


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


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Single-user mode: ensure the default account exists.
    if settings.single_user_mode:
        await _ensure_single_user()

    yield
    # TODO: tear down resources


def create_app() -> FastAPI:
    application = FastAPI(
        title="DailyLoadout API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
    )

    # Rate limiting
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    # Routers
    application.include_router(auth_router)

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
