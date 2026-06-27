"""Unit tests for the OAuth provider configs, userinfo parsing, and PKCE."""

from __future__ import annotations

import base64
import hashlib

import pytest

from dailyloadout.config import settings
from dailyloadout.infrastructure.oauth import (
    OAuthError,
    build_authorize_url,
    build_provider,
    generate_pkce_pair,
    parse_userinfo,
)

# ── build_provider ──────────────────────────────────────────────────────


def test_build_provider_none_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "google_oauth_client_id", "")
    assert build_provider("google", settings) is None


def test_build_provider_google_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "google_oauth_client_id", "gid")
    monkeypatch.setattr(settings, "google_oauth_client_secret", "gsecret")
    provider = build_provider("google", settings)
    assert provider is not None
    assert provider.name == "google"
    assert provider.client_id == "gid"
    assert "email" in provider.scopes


def test_build_provider_twitch_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "twitch_oauth_client_id", "tid")
    provider = build_provider("twitch", settings)
    assert provider is not None
    assert provider.name == "twitch"
    assert provider.scopes == ("user:read:email",)


def test_build_provider_unknown_name() -> None:
    assert build_provider("facebook", settings) is None


# ── parse_userinfo ──────────────────────────────────────────────────────


def test_parse_google_verified() -> None:
    info = parse_userinfo(
        "google",
        {"sub": "123", "email": "a@b.com", "email_verified": True, "name": "Ana", "picture": "u"},
    )
    assert info.provider_uid == "123"
    assert info.email == "a@b.com"
    assert info.email_verified is True
    assert info.display_name == "Ana"
    assert info.avatar_url == "u"


def test_parse_google_unverified_defaults_false() -> None:
    info = parse_userinfo("google", {"sub": "1", "email": "a@b.com"})
    assert info.email_verified is False


def test_parse_google_missing_sub_raises() -> None:
    with pytest.raises(OAuthError):
        parse_userinfo("google", {"email": "a@b.com"})


def test_parse_twitch_email_present_is_verified() -> None:
    info = parse_userinfo(
        "twitch",
        {"data": [{"id": "99", "login": "gamer", "display_name": "Gamer", "email": "g@t.tv"}]},
    )
    assert info.provider_uid == "99"
    assert info.email == "g@t.tv"
    assert info.email_verified is True
    assert info.display_name == "Gamer"


def test_parse_twitch_no_email_is_unverified() -> None:
    info = parse_userinfo("twitch", {"data": [{"id": "99", "login": "gamer"}]})
    assert info.email is None
    assert info.email_verified is False


def test_parse_twitch_empty_data_raises() -> None:
    with pytest.raises(OAuthError):
        parse_userinfo("twitch", {"data": []})


def test_parse_twitch_missing_id_raises() -> None:
    with pytest.raises(OAuthError):
        parse_userinfo("twitch", {"data": [{"login": "g"}]})


def test_parse_unknown_provider_raises() -> None:
    with pytest.raises(OAuthError):
        parse_userinfo("facebook", {})


# ── PKCE + authorize URL ────────────────────────────────────────────────


def test_generate_pkce_pair_is_s256() -> None:
    verifier, challenge = generate_pkce_pair()
    expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=")
    assert challenge == expected.decode()
    assert "=" not in challenge  # base64url, unpadded


def test_generate_pkce_pair_is_random() -> None:
    assert generate_pkce_pair()[0] != generate_pkce_pair()[0]


def test_build_authorize_url_carries_pkce_and_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "google_oauth_client_id", "gid")
    provider = build_provider("google", settings)
    assert provider is not None
    url = build_authorize_url(provider, "https://api/cb", "st4te", "chall")
    assert url.startswith(provider.authorize_url)
    assert "client_id=gid" in url
    assert "code_challenge=chall" in url
    assert "code_challenge_method=S256" in url
    assert "state=st4te" in url
    assert "response_type=code" in url
