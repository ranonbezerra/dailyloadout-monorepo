"""FastAPI dependencies for DailyLoadout.

Re-exports all dependency aliases so existing imports keep working:

    from dailyloadout.deps import AuthServiceDep, CurrentUserDep
"""

from .auth import AuthServiceDep, CurrentUserDep
from .capture import (
    CaptureCandidateRepoDep,
    CaptureRepoDep,
    CaptureServiceDep,
    IGDBClientDep,
    LLMClientDep,
)
from .db import DbSession, get_db
from .library import (
    GameRepoDep,
    LibraryRepoDep,
    LibraryServiceDep,
    PlatformRepoDep,
)

__all__ = [
    "AuthServiceDep",
    "CaptureCandidateRepoDep",
    "CaptureRepoDep",
    "CaptureServiceDep",
    "CurrentUserDep",
    "DbSession",
    "GameRepoDep",
    "IGDBClientDep",
    "LLMClientDep",
    "LibraryRepoDep",
    "LibraryServiceDep",
    "PlatformRepoDep",
    "get_db",
]
