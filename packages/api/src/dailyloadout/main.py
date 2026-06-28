import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse
from scalar_fastapi import get_scalar_api_reference

from dailyloadout.api._access_log import install_access_log_redaction
from dailyloadout.api.middleware import (
    DefaultUserRateLimitMiddleware,
    MaxBodySizeMiddleware,
    SecurityHeadersMiddleware,
)
from dailyloadout.api.v1.admin import router as admin_router
from dailyloadout.api.v1.admin_captures import router as admin_captures_router
from dailyloadout.api.v1.admin_missions import router as admin_missions_router
from dailyloadout.api.v1.auth import router as auth_router
from dailyloadout.api.v1.auth_oauth import router as auth_oauth_router
from dailyloadout.api.v1.cache import router as cache_router
from dailyloadout.api.v1.capture import router as capture_router
from dailyloadout.api.v1.concierge import router as concierge_router
from dailyloadout.api.v1.library import router as library_router
from dailyloadout.api.v1.library_import import router as library_import_router
from dailyloadout.api.v1.loadout import router as loadout_router
from dailyloadout.api.v1.mission import router as mission_router
from dailyloadout.api.v1.stats import router as stats_router
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
                    repo,
                    max_hours=settings.mission_auto_clamp_hours,
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
                ignored = await auto_ignore_stale_loadouts(
                    repo, max_hours=settings.loadout_auto_ignore_hours
                )
                await session.commit()
                if ignored:
                    logger.info("auto_ignore_cycle_done", ignored=ignored)
        except Exception:
            logger.exception("auto_ignore_cycle_error")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Redact query strings (OAuth code/state, tokens) from uvicorn access logs.
    install_access_log_redaction()
    # Optional error reporting — OFF unless SENTRY_DSN is set; always scrubs PII.
    from dailyloadout.infrastructure.observability import init_sentry

    init_sentry()

    # Single-user mode: ensure the default account exists.
    if settings.single_user_mode:
        await _ensure_single_user()

    # Preload Ollama models in the background so the first request isn't cold.
    if settings.llm_provider == "ollama" and settings.ollama_warmup_models:
        from dailyloadout.infrastructure.llm.warmup import warm_ollama_models

        asyncio.create_task(  # noqa: RUF006 - fire-and-forget; best-effort warmup
            warm_ollama_models(
                base_url=settings.ollama_base_url,
                models=settings.ollama_warmup_models,
                keep_alive=settings.ollama_warmup_keep_alive,
            )
        )

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


def _docs_enabled() -> bool:
    """Docs/OpenAPI are exposed only in dev/test, or when explicitly enabled."""
    return settings.docs_enabled and settings.app_env in ("development", "testing")


def create_app() -> FastAPI:
    docs_on = _docs_enabled()
    application = FastAPI(
        title="DailyLoadout API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        # Disable the schema entirely in production so /openapi.json 404s and
        # Scalar has nothing to render.
        openapi_url="/openapi.json" if docs_on else None,
    )

    # Host allowlist (defense-in-depth behind Caddy; default ["*"] = allow all in
    # dev). Set TRUSTED_HOSTS to the API domain(s) in prod to reject Host-header
    # spoofing / routing confusion.
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.trusted_hosts,
    )

    # Security response headers (HSTS, nosniff, frame-deny, referrer policy, CSP).
    application.add_middleware(
        SecurityHeadersMiddleware,
        hsts_max_age=settings.hsts_max_age_seconds,
    )

    # Coarse request-body size cap (DoS backstop), before any body is read.
    application.add_middleware(
        MaxBodySizeMiddleware,
        max_body_bytes=settings.max_request_body_bytes,
    )

    # Generous per-user rate-limit backstop so a NEW authenticated route is
    # metered by default even if its author forgets an explicit limiter. No-op
    # when rate limiting is disabled (tests); fails open on a limiter error.
    application.add_middleware(
        DefaultUserRateLimitMiddleware,
        per_minute=settings.rate_limit_default_per_minute,
    )

    # CORS — X-Auth-Mode is sent by the web client on every request to select
    # cookie vs body refresh mode; omitting it breaks cross-origin cookie mode.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Auth-Mode"],
    )

    # Routers
    application.include_router(admin_router)
    application.include_router(admin_captures_router)
    application.include_router(admin_missions_router)
    application.include_router(auth_router)
    application.include_router(auth_oauth_router)
    application.include_router(cache_router)
    application.include_router(capture_router)
    application.include_router(library_import_router)
    application.include_router(library_router)
    application.include_router(mission_router)
    application.include_router(loadout_router)
    application.include_router(stats_router)
    application.include_router(concierge_router)

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    if docs_on:

        @application.get("/docs", include_in_schema=False)
        async def scalar_docs() -> HTMLResponse:
            return get_scalar_api_reference(
                openapi_url=application.openapi_url or "/openapi.json",
                title=application.title,
            )

    return application


app = create_app()
