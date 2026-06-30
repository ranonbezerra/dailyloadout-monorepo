"""Structured logging context for background jobs."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter
from uuid import uuid4

import structlog

logger = structlog.get_logger()


@contextmanager
def job_context(job_name: str, **fields: object) -> Iterator[str]:
    """Bind common job fields and emit lifecycle events for one job run."""
    job_id = str(uuid4())
    tokens = structlog.contextvars.bind_contextvars(
        job_id=job_id,
        job_name=job_name,
        **fields,
    )
    started_at = perf_counter()
    logger.info("job_started")
    try:
        yield job_id
    except Exception:
        logger.error("job_failed", duration_ms=_elapsed_ms(started_at), exc_info=True)
        raise
    else:
        logger.info("job_completed", duration_ms=_elapsed_ms(started_at))
    finally:
        structlog.contextvars.reset_contextvars(**tokens)


def _elapsed_ms(started_at: float) -> int:
    return int((perf_counter() - started_at) * 1000)
