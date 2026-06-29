"""FastAPI dependencies for Slate.

Re-exports all dependency aliases so existing imports keep working:

    from slate.deps import AuthServiceDep, CurrentUserDep
"""

from .auth import (
    AuthServiceDep,
    CurrentUserDep,
    PasswordRecoveryServiceDep,
    RequireVerifiedUserDep,
)
from .capture import (
    CaptureCandidateRepoDep,
    CaptureRepoDep,
    IGDBClientDep,
    LLMClientDep,
    STTClientDep,
)
from .db import DbSession, get_db
from .library import (
    GameRepoDep,
    LibraryRepoDep,
    LibraryServiceDep,
    PlatformRepoDep,
)
from .ocr import CaptureServiceDep
from .pick import (
    PickRepoDep,
    PickServiceDep,
)
from .play_session import (
    PlaySessionRepoDep,
    PlaySessionServiceDep,
)
from .stats import StatsRepoDep, StatsServiceDep

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
    "PasswordRecoveryServiceDep",
    "PickRepoDep",
    "PickServiceDep",
    "PlatformRepoDep",
    "PlaySessionRepoDep",
    "PlaySessionServiceDep",
    "RequireVerifiedUserDep",
    "STTClientDep",
    "StatsRepoDep",
    "StatsServiceDep",
    "get_db",
]
