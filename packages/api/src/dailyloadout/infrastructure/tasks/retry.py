"""Retry middleware with exponential backoff for Taskiq tasks.

Extends the standard ``SimpleRetryMiddleware`` by sleeping before
re-enqueueing a failed task.  The delay doubles on each attempt:

    attempt 1 → 2s, attempt 2 → 4s, attempt 3 → 8s, ...

This prevents thundering-herd retries against a temporarily
unavailable LLM or database.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import structlog
from taskiq import TaskiqMiddleware
from taskiq.exceptions import NoResultError

if TYPE_CHECKING:
    from taskiq import TaskiqMessage, TaskiqResult

logger = structlog.get_logger()

_BASE_DELAY_SECONDS = 2.0


class ExponentialBackoffRetryMiddleware(TaskiqMiddleware):
    """Retry failed tasks with exponential backoff.

    Parameters
    ----------
    max_retries:
        Maximum number of retry attempts (default 3).
    base_delay:
        Initial delay in seconds; doubled on each retry.
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = _BASE_DELAY_SECONDS,
    ) -> None:
        self.max_retries = max_retries
        self.base_delay = base_delay

    async def on_error(
        self,
        message: TaskiqMessage,
        result: TaskiqResult[Any],
        exception: BaseException,
    ) -> None:
        """Re-enqueue the task after an exponential delay."""
        if isinstance(exception, NoResultError):
            return

        retry_on_error = message.labels.get("retry_on_error")
        if isinstance(retry_on_error, str):
            retry_on_error = retry_on_error.lower() == "true"
        if not retry_on_error:
            return

        retries = int(message.labels.get("_retries", 0)) + 1
        max_retries = int(
            message.labels.get("max_retries", self.max_retries),
        )

        if retries >= max_retries:
            logger.warning(
                "task_retries_exhausted",
                task=message.task_name,
                retries=retries,
            )
            return

        delay = self.base_delay * (2 ** (retries - 1))
        logger.info(
            "task_retry_backoff",
            task=message.task_name,
            retry=retries,
            delay_s=delay,
        )
        await asyncio.sleep(delay)

        from taskiq.kicker import AsyncKicker

        kicker: AsyncKicker[Any, Any] = AsyncKicker(
            task_name=message.task_name,
            broker=self.broker,
            labels=message.labels,
        ).with_task_id(message.task_id)
        kicker.with_labels(_retries=retries)

        await kicker.kiq(*message.args, **message.kwargs)

        # Suppress the error result so the retry is transparent.
        result.error = NoResultError()
