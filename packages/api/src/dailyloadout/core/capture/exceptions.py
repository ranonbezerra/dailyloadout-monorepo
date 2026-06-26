"""Domain errors for the capture/import layer.

Raised by the service so routers can map them to HTTP status codes without the
service importing FastAPI/HTTP concerns for ingestion guards.
"""

from __future__ import annotations


class CaptureIngestionError(Exception):
    """Base class for capture/import ingestion failures."""


class InvalidUploadError(CaptureIngestionError):
    """An uploaded file failed a MIME-type or size guard (router maps to 400/422)."""


class ImportQuotaExceededError(CaptureIngestionError):
    """The per-day library-import image cap was exceeded (router maps to 429)."""
