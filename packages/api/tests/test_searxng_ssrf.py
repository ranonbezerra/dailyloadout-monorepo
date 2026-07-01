"""SSRF guard for the web-scraper: only public IPs pass; the IP is pinned."""

from __future__ import annotations

import socket
from typing import Any

import pytest

from slate.infrastructure.research import searxng

_PUBLIC = "93.184.216.34"


def _addrinfo(*ips: str) -> list[tuple[Any, ...]]:
    return [(socket.AF_INET, None, None, "", (ip, 0)) for ip in ips]


def _patch(monkeypatch: pytest.MonkeyPatch, *ips: str) -> None:
    monkeypatch.setattr(searxng.socket, "getaddrinfo", lambda *a, **k: _addrinfo(*ips))


class TestResolvePublicIp:
    def test_public_ip_is_returned_for_pinning(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch(monkeypatch, _PUBLIC)
        assert searxng._resolve_public_ip("example.com") == _PUBLIC

    @pytest.mark.parametrize("ip", ["10.0.0.5", "127.0.0.1", "169.254.169.254", "192.168.1.1"])
    def test_non_public_ip_is_blocked(self, monkeypatch: pytest.MonkeyPatch, ip: str) -> None:
        _patch(monkeypatch, ip)
        assert searxng._resolve_public_ip("internal") is None

    def test_any_private_in_the_set_blocks(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # A host resolving to BOTH public and private is rejected (rebind defense).
        _patch(monkeypatch, _PUBLIC, "169.254.1.1")
        assert searxng._resolve_public_ip("mixed") is None

    def test_resolution_failure_is_blocked(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _fail(*a: Any, **k: Any) -> None:
            raise socket.gaierror

        monkeypatch.setattr(searxng.socket, "getaddrinfo", _fail)
        assert searxng._resolve_public_ip("nope") is None
