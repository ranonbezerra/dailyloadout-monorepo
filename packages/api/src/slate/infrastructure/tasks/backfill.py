"""Taskiq wrapper for the batch re-inference / backfill job (Epic 28).

Lets a large backfill run on the existing worker fleet instead of a blocking CLI
process. The CLI (``scripts/backfill.py``) is the interactive/dry-run entry point;
this task is the "run it on the workers" path. Both drive the same
``BackfillService``.
"""

from __future__ import annotations

import structlog

from slate.core.backfill.service import BackfillKind
from slate.infrastructure.observability import job_context
from slate.infrastructure.tasks.broker import broker

logger = structlog.get_logger()


@broker.task
async def backfill_task(kind: BackfillKind, limit: int | None = None) -> None:
    """Reprocess stale embeddings or extractions on a background worker."""
    from slate.config import settings as app_settings
    from slate.core.backfill.service import BackfillService
    from slate.infrastructure.db.session import async_session_factory
    from slate.infrastructure.embedding.factory import get_embedding_client
    from slate.infrastructure.llm.factory import get_llm_client

    with job_context("backfill", kind=kind):
        service = BackfillService(
            async_session_factory,
            get_llm_client(app_settings),
            get_embedding_client(app_settings),
            app_settings,
        )
        report = await service.run(kind, limit=limit)
        logger.info(
            "backfill_task_done",
            processed=report.processed,
            failed=report.failed,
            stopped=report.stopped,
        )
