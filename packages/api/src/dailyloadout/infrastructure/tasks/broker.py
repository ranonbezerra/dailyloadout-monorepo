"""Taskiq broker configuration.

Uses Redis as the message broker in production. Falls back to an
in-memory broker when the ``APP_ENV`` is ``"testing"`` so that tests
never open real Redis connections.
"""

from taskiq import AsyncBroker, InMemoryBroker

from dailyloadout.config import settings

broker: AsyncBroker

if settings.app_env == "testing":
    broker = InMemoryBroker()
else:
    from taskiq_redis import ListQueueBroker

    broker = ListQueueBroker(url=settings.redis_url)
