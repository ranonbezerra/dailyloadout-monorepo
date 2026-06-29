"""SQLAlchemy ORM models, split by domain.

All models are re-exported here so existing imports stay unchanged:
``from slate.infrastructure.db.models import User, Game, ...``
"""

from slate.infrastructure.db.models.auth import (
    AdminAuditLog,
    AdminUser,
    OAuthIdentity,
    RefreshToken,
    User,
)
from slate.infrastructure.db.models.capture import Capture, CaptureCandidate
from slate.infrastructure.db.models.config import AppConfig
from slate.infrastructure.db.models.library import Game, LibraryEntry, Platform
from slate.infrastructure.db.models.pick import Pick
from slate.infrastructure.db.models.play_session import PlaySession
from slate.infrastructure.db.models.usage import UsageCounter

__all__ = [
    "AdminAuditLog",
    "AdminUser",
    "AppConfig",
    "Capture",
    "CaptureCandidate",
    "Game",
    "LibraryEntry",
    "OAuthIdentity",
    "Pick",
    "Platform",
    "PlaySession",
    "RefreshToken",
    "UsageCounter",
    "User",
]
