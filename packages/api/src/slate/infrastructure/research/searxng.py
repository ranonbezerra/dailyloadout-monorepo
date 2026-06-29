"""SearXNG-backed research client (local, no external search keys)."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit

import httpx
import structlog

from slate.config import Settings

from ._html import extract_text
from .base import AbstractResearchClient, ResearchUnavailableError, SearchResult

logger = structlog.get_logger()

_SCRAPE_MAX_CHARS = 4000


def _is_public_host(hostname: str) -> bool:
    """Return ``True`` only if *hostname* resolves exclusively to public IPs.

    SSRF guard: ``fetch`` follows search-result URLs, which are attacker-influenced
    (they come from the open web). We resolve the host and reject it if ANY
    resolved address is loopback, private, link-local, reserved, or otherwise
    non-global, so a result can't trick us into hitting internal services.
    """
    try:
        infos = socket.getaddrinfo(hostname, None)
    except (socket.gaierror, UnicodeError):
        return False

    addresses = {info[4][0] for info in infos}
    if not addresses:
        return False

    for addr in addresses:
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            return False
        if not ip.is_global or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return False
    return True


class SearxngResearchClient(AbstractResearchClient):
    """Query a local SearXNG instance via its JSON API."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.searxng_base_url.rstrip("/")
        self._timeout = settings.llm_timeout_seconds
        self._http_client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Return a reusable HTTP client (connection pooling)."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=self._timeout)
        return self._http_client

    async def search(self, query: str, limit: int = 6) -> list[SearchResult]:
        """Return up to *limit* results from SearXNG's JSON search API."""
        client = await self._get_client()
        try:
            resp = await client.get(
                f"{self._base_url}/search",
                params={"q": query, "format": "json", "safesearch": 1},
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("searxng_request_failed", error=str(exc))
            raise ResearchUnavailableError(str(exc)) from exc

        body = resp.json()
        raw_results = body.get("results", []) if isinstance(body, dict) else []

        results: list[SearchResult] = []
        for item in raw_results[:limit]:
            if not isinstance(item, dict):
                continue
            results.append(
                SearchResult(
                    title=str(item.get("title", "")),
                    url=str(item.get("url", "")),
                    snippet=str(item.get("content", "")),
                )
            )
        return results

    async def fetch(self, url: str) -> str:
        """Fetch *url* and return cleaned page text for recap grounding.

        SSRF guard: result URLs come from the open web, so before fetching we
        validate the target host resolves to a public IP. Redirects are disabled
        so a public URL can't 30x us into an internal address; on the rare
        legitimate redirect we simply skip the page rather than chase it blindly.
        """
        if not url.startswith(("http://", "https://")):
            return ""

        hostname = urlsplit(url).hostname
        if not hostname or not _is_public_host(hostname):
            logger.warning("searxng_scrape_blocked", url=url)
            return ""

        client = await self._get_client()
        try:
            resp = await client.get(url, follow_redirects=False)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("searxng_scrape_failed", url=url, error=str(exc))
            return ""
        return extract_text(resp.text, max_chars=_SCRAPE_MAX_CHARS)
