"""SQLAlchemy ORM models, split by domain.

All models are re-exported here so existing imports stay unchanged:
``from dailyloadout.infrastructure.db.models import User, Game, ...``
"""

from dailyloadout.infrastructure.db.models.auth import (
    AdminUser,
    OAuthIdentity,
    RefreshToken,
    User,
)
from dailyloadout.infrastructure.db.models.capture import Capture, CaptureCandidate
from dailyloadout.infrastructure.db.models.library import Game, LibraryEntry, Platform
from dailyloadout.infrastructure.db.models.loadout import Loadout
from dailyloadout.infrastructure.db.models.mission import Mission
from dailyloadout.infrastructure.db.models.usage import UsageCounter

__all__ = [
    "AdminUser",
    "Capture",
    "CaptureCandidate",
    "Game",
    "LibraryEntry",
    "Loadout",
    "Mission",
    "OAuthIdentity",
    "Platform",
    "RefreshToken",
    "UsageCounter",
    "User",
]
