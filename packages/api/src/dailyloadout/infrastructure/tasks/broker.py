"""Taskiq broker configuration.

Uses Redis as the message broker in production. Falls back to an
in-memory broker when the ``APP_ENV`` is ``"testing"`` so that tests
never open real Redis connections.

Retry middleware is configured globally so all tasks get automatic
retries with exponential backoff (2s → 4s → 8s) on failure.
"""

from taskiq import AsyncBroker, InMemoryBroker

from dailyloadout.config import settings
from dailyloadout.infrastructure.tasks.retry import ExponentialBackoffRetryMiddleware

_retry = ExponentialBackoffRetryMiddleware(max_retries=3, base_delay=2.0)

broker: AsyncBroker

if settings.app_env == "testing":
    broker = InMemoryBroker().with_middlewares(_retry)
else:
    from taskiq_redis import ListQueueBroker

    broker = ListQueueBroker(url=settings.redis_url).with_middlewares(_retry)
