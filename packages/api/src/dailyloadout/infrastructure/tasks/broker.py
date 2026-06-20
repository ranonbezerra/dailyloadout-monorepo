"""Taskiq broker configuration.

Uses Redis as the message broker. The broker URL comes from the
application settings (``redis_url``).
"""

from taskiq_redis import ListQueueBroker

from dailyloadout.config import settings

broker = ListQueueBroker(url=settings.redis_url)
