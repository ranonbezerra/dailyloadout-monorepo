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


def _resolve_public_ip(hostname: str) -> str | None:
    """Resolve *hostname*; return ONE validated IP to pin the connection to, else None.

    SSRF guard: ``fetch`` follows search-result URLs, which are attacker-influenced
    (they come from the open web). We resolve the host and reject it if ANY resolved
    address is loopback, private, link-local, reserved, or otherwise non-global.
    Returning the validated IP (rather than a bool) lets the caller pin the request
    to *this* address, closing the TOCTOU window where a fast-flipping DNS record
    could resolve public here and private again inside ``httpx.get`` (DNS rebinding).
    """
    try:
        infos = socket.getaddrinfo(hostname, None)
    except (socket.gaierror, UnicodeError):
        return None

    addresses = [str(info[4][0]) for info in infos]
    if not addresses:
        return None

    for addr in addresses:
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            return None
        if not ip.is_global or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return None
    return addresses[0]


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
        resolve the host, reject any non-public IP, and PIN the connection to the
        validated address (so a rebinding DNS record can't flip it private inside
        httpx). SNI + cert stay on the original hostname. Redirects are disabled so
        a public URL can't 30x us into an internal address.
        """
        if not url.startswith(("http://", "https://")):
            return ""

        hostname = urlsplit(url).hostname
        pinned_ip = _resolve_public_ip(hostname) if hostname else None
        if hostname is None or pinned_ip is None:
            logger.warning("searxng_scrape_blocked", url=url)
            return ""

        client = await self._get_client()
        try:
            # Connect to the validated IP, but keep Host + TLS SNI/cert on the real
            # hostname — the request never re-resolves, closing the TOCTOU.
            request = client.build_request("GET", url)
            request.url = request.url.copy_with(host=pinned_ip)
            request.headers["Host"] = hostname
            request.extensions["sni_hostname"] = hostname
            resp = await client.send(request, follow_redirects=False)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("searxng_scrape_failed", url=url, error=str(exc))
            return ""
        return extract_text(resp.text, max_chars=_SCRAPE_MAX_CHARS)
