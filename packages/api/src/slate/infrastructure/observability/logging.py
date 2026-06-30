"""Structured application logging for API, workers, and scripts.

Production emits JSON lines for log shippers. Development/test keeps a compact
console renderer. Request-scoped fields are supplied by ``structlog.contextvars``
so service/worker logs inherit ``request_id`` without threading it through call
stacks.
"""

from __future__ import annotations

import logging
import os
from collections.abc import MutableMapping
from typing import Any

import structlog
from structlog.typing import Processor

_DEV_ENVS = {"development", "testing"}
_CONFIGURED = False


def configure_logging(*, app_env: str, service: str = "slate-api") -> None:
    """Configure stdlib logging + structlog once for the current process."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        _add_static_fields(app_env=app_env, service=service),
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    renderer = (
        structlog.dev.ConsoleRenderer(colors=False)
        if app_env.strip().lower() in _DEV_ENVS
        else structlog.processors.JSONRenderer()
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    structlog.configure(
        processors=[*shared_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    _CONFIGURED = True


def _add_static_fields(*, app_env: str, service: str) -> Processor:
    def processor(
        _logger: Any,
        _method_name: str,
        event_dict: MutableMapping[str, Any],
    ) -> MutableMapping[str, Any]:
        event_dict.setdefault("app_env", app_env)
        event_dict.setdefault("service", service)
        return event_dict

    return processor
