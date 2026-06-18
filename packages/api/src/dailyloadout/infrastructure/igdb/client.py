"""IGDB API client with Twitch OAuth authentication and rate limiting."""

from __future__ import annotations

import asyncio
import contextlib
import time
from datetime import UTC, date, datetime

import httpx
import structlog

from dailyloadout.config import Settings

from .exceptions import IGDBNotConfigured
from .schemas import IGDBGame

logger = structlog.get_logger()

_TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
_IGDB_BASE_URL = "https://api.igdb.com/v4"

# IGDB allows 4 requests per second.
_MAX_REQUESTS_PER_SECOND = 4
_REQUEST_INTERVAL = 1.0 / _MAX_REQUESTS_PER_SECOND


class IGDBClient:
    """Client for the IGDB API with automatic Twitch OAuth and rate limiting."""

    def __init__(self, settings: Settings) -> None:
        if not settings.igdb_client_id or not settings.igdb_client_secret:
            raise IGDBNotConfigured("IGDB credentials not provided. Enrichment skipped.")

        self._client_id = settings.igdb_client_id
        self._client_secret = settings.igdb_client_secret
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0
        self._last_request_time: float = 0.0
        self._lock = asyncio.Lock()

    async def _ensure_token(self, client: httpx.AsyncClient) -> str:
        """Authenticate via Twitch OAuth if the cached token has expired."""
        if self._access_token and time.monotonic() < self._token_expires_at:
            return self._access_token

        async with self._lock:
            # Double-check after acquiring the lock.
            if self._access_token and time.monotonic() < self._token_expires_at:
                return self._access_token

            resp = await client.post(
                _TWITCH_TOKEN_URL,
                params={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "grant_type": "client_credentials",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            self._access_token = str(data["access_token"])
            # Expire 5 minutes early to avoid edge-case failures.
            expires_in = int(data.get("expires_in", 3600))
            self._token_expires_at = time.monotonic() + expires_in - 300

            logger.info("igdb_token_refreshed", expires_in=expires_in)
            return self._access_token

    async def _rate_limit(self) -> None:
        """Simple rate limiter: sleep if requests come too fast."""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < _REQUEST_INTERVAL:
            await asyncio.sleep(_REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.monotonic()

    async def search_games(self, query: str, limit: int = 5) -> list[IGDBGame]:
        """Search IGDB for games matching *query*.

        Returns up to *limit* results enriched with cover URL, summary,
        genres, and release date.
        """
        # Apicalypse query body.
        body = (
            f'search "{query}";'
            f" fields name,cover.image_id,summary,genres.name,first_release_date;"
            f" limit {limit};"
        )

        async with httpx.AsyncClient(timeout=30) as client:
            token = await self._ensure_token(client)
            await self._rate_limit()

            resp = await client.post(
                f"{_IGDB_BASE_URL}/games",
                headers={
                    "Client-ID": self._client_id,
                    "Authorization": f"Bearer {token}",
                },
                content=body,
            )
            resp.raise_for_status()
            data = resp.json()

        results: list[IGDBGame] = []
        for item in data:
            cover_url: str | None = None
            cover = item.get("cover")
            if isinstance(cover, dict) and cover.get("image_id"):
                cover_url = (
                    f"https://images.igdb.com/igdb/image/upload/t_cover_big/"
                    f"{cover['image_id']}.jpg"
                )

            genres: list[str] | None = None
            raw_genres = item.get("genres")
            if isinstance(raw_genres, list):
                genres = [g["name"] for g in raw_genres if isinstance(g, dict) and "name" in g]

            release_date: date | None = None
            raw_date = item.get("first_release_date")
            if raw_date is not None:
                with contextlib.suppress(ValueError, OSError):
                    release_date = datetime.fromtimestamp(int(raw_date), tz=UTC).date()

            results.append(
                IGDBGame(
                    igdb_id=int(item["id"]),
                    title=str(item.get("name", "")),
                    cover_url=cover_url,
                    summary=item.get("summary"),
                    genres=genres,
                    first_release_date=release_date,
                )
            )

        return results
