"""SQLAlchemy ORM models, split by domain.

All models are re-exported here so existing imports stay unchanged:
``from dailyloadout.infrastructure.db.models import User, Game, ...``
"""

from dailyloadout.infrastructure.db.models.auth import OAuthIdentity, RefreshToken, User
from dailyloadout.infrastructure.db.models.capture import Capture, CaptureCandidate
from dailyloadout.infrastructure.db.models.library import Game, LibraryEntry, Platform

__all__ = [
    "Capture",
    "CaptureCandidate",
    "Game",
    "LibraryEntry",
    "OAuthIdentity",
    "Platform",
    "RefreshToken",
    "User",
]
