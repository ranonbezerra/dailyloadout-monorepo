"""Phase 2 / Block 3 — registration identity-hygiene tests.

Covers the disposable-email blocklist, the fail-open MX probe (DNS fully
mocked — no network in CI), and display-name sanitization (control / bidi /
zero-width rejection + NFKC normalisation).
"""

from __future__ import annotations

from typing import Any

import dns.exception
import dns.resolver
import pytest
from httpx import AsyncClient

from dailyloadout.config import settings
from dailyloadout.core.auth.service import EmailRejectedError
from dailyloadout.core.sanitization import sanitize_display_name
from dailyloadout.infrastructure.email.disposable_domains import (
    DISPOSABLE_EMAIL_DOMAINS,
    is_disposable_domain,
)
from dailyloadout.infrastructure.email.validation import (
    domain_has_mail_records,
    is_disposable_email,
)

# Short alias so the heavily-parametrised DNS-mock signatures fit one line.
MP = pytest.MonkeyPatch


# =====================================================================
# Disposable email blocklist
# =====================================================================
class TestDisposableBlocklist:
    def test_known_disposable_domain_detected(self) -> None:
        assert is_disposable_domain("mailinator.com")
        assert is_disposable_email("burner@guerrillamail.com")
        assert is_disposable_email("x@10minutemail.com")

    def test_case_insensitive_and_trimmed(self) -> None:
        assert is_disposable_email("USER@Mailinator.COM")
        assert is_disposable_domain("  YOPMAIL.com  ")

    def test_subdomain_alias_not_falsely_matched(self) -> None:
        # Exact registrable-domain match only; a normal provider is fine.
        assert not is_disposable_email("real.person@gmail.com")
        assert not is_disposable_domain("example.org")

    def test_malformed_email_is_not_disposable(self) -> None:
        assert not is_disposable_email("no-at-sign")

    def test_blocklist_is_extendable_set(self) -> None:
        assert isinstance(DISPOSABLE_EMAIL_DOMAINS, frozenset)
        assert "mailinator.com" in DISPOSABLE_EMAIL_DOMAINS

    async def test_register_rejects_disposable_domain(self, async_client: AsyncClient) -> None:
        resp = await async_client.post(
            "/v1/auth/register",
            json={
                "email": "throwaway@mailinator.com",
                "password": "SecurePass1",
                "display_name": "Throwaway",
            },
        )
        assert resp.status_code == 422
        assert "disposable" in resp.json()["detail"].lower()

    async def test_register_accepts_normal_domain(self, async_client: AsyncClient) -> None:
        resp = await async_client.post(
            "/v1/auth/register",
            json={
                "email": "legit@example.com",
                "password": "SecurePass1",
                "display_name": "Legit User",
            },
        )
        assert resp.status_code == 201

    async def test_blocklist_toggle_disables_check(
        self, async_client: AsyncClient, monkeypatch: MP
    ) -> None:
        monkeypatch.setattr(settings, "block_disposable_emails", False)
        resp = await async_client.post(
            "/v1/auth/register",
            json={
                "email": "now-allowed@mailinator.com",
                "password": "SecurePass1",
                "display_name": "Now Allowed",
            },
        )
        assert resp.status_code == 201


# =====================================================================
# MX deliverability probe (DNS fully mocked)
# =====================================================================
class TestMxCheck:
    async def test_mx_check_disabled_in_test_env(self) -> None:
        # APP_ENV=testing => is_production is False => probe is skipped at the
        # service layer. The standalone helper still fails OPEN regardless.
        assert settings.is_production is False

    async def test_fails_open_on_dns_timeout(self, monkeypatch: MP) -> None:
        def _boom(self: Any, qname: str, rdtype: str) -> Any:
            raise dns.exception.Timeout("simulated timeout")

        monkeypatch.setattr(dns.resolver.Resolver, "resolve", _boom)
        # A DNS hiccup must ALLOW the address.
        assert await domain_has_mail_records("user@some-domain.test") is True

    async def test_fails_open_on_no_nameservers(self, monkeypatch: MP) -> None:
        def _boom(self: Any, qname: str, rdtype: str) -> Any:
            raise dns.resolver.NoNameservers("all servers failed")

        monkeypatch.setattr(dns.resolver.Resolver, "resolve", _boom)
        assert await domain_has_mail_records("user@flaky.test") is True

    async def test_rejects_domain_with_no_mail_records(self, monkeypatch: MP) -> None:
        def _no_records(self: Any, qname: str, rdtype: str) -> Any:
            # No MX, and no A/AAAA fallback either → definitively undeliverable.
            raise dns.resolver.NoAnswer("no records")

        monkeypatch.setattr(dns.resolver.Resolver, "resolve", _no_records)
        assert await domain_has_mail_records("user@dead-domain.test") is False

    async def test_accepts_domain_with_mx(self, monkeypatch: MP) -> None:
        def _has_mx(self: Any, qname: str, rdtype: str) -> list[str]:
            if rdtype == "MX":
                return ["mx1.example.test"]
            raise dns.resolver.NoAnswer("only MX queried")

        monkeypatch.setattr(dns.resolver.Resolver, "resolve", _has_mx)
        assert await domain_has_mail_records("user@example.test") is True

    async def test_accepts_domain_with_only_a_record(self, monkeypatch: MP) -> None:
        def _no_mx_has_a(self: Any, qname: str, rdtype: str) -> list[str]:
            if rdtype == "MX":
                raise dns.resolver.NoAnswer("no mx")
            if rdtype == "A":
                return ["203.0.113.10"]
            raise dns.resolver.NoAnswer("no aaaa")

        monkeypatch.setattr(dns.resolver.Resolver, "resolve", _no_mx_has_a)
        assert await domain_has_mail_records("user@a-only.test") is True

    async def test_address_fallback_fails_open_on_dns_error(self, monkeypatch: MP) -> None:
        def _mx_empty_then_error(self: Any, qname: str, rdtype: str) -> Any:
            if rdtype == "MX":
                raise dns.resolver.NoAnswer("no mx")
            raise dns.exception.DNSException("a-lookup blew up")

        monkeypatch.setattr(dns.resolver.Resolver, "resolve", _mx_empty_then_error)
        assert await domain_has_mail_records("user@weird.test") is True

    async def test_malformed_email_fails_open(self) -> None:
        assert await domain_has_mail_records("garbage-no-domain") is True

    async def test_mx_probe_rejects_in_production(self, monkeypatch: MP) -> None:
        # Force the production gate so the (mocked) probe is exercised, and make
        # the probe report "undeliverable" → EmailRejectedError.
        from dailyloadout.infrastructure.email import validation

        monkeypatch.setattr(settings, "app_env", "production")
        monkeypatch.setattr(settings, "check_email_mx", True)

        async def _no_mail(email: str) -> bool:
            return False

        monkeypatch.setattr(validation, "domain_has_mail_records", _no_mail)

        with pytest.raises(EmailRejectedError):
            await validation.assert_email_acceptable("user@undeliverable.test")

    async def test_mx_probe_skipped_outside_production(self, monkeypatch: MP) -> None:
        # In the test env (is_production False) the probe never runs, even for a
        # domain that would report undeliverable.
        from dailyloadout.infrastructure.email import validation

        called = False

        async def _spy(email: str) -> bool:
            nonlocal called
            called = True
            return False

        monkeypatch.setattr(validation, "domain_has_mail_records", _spy)
        await validation.assert_email_acceptable("ok@example.com")
        assert called is False


# =====================================================================
# display_name sanitization
# =====================================================================
class TestDisplayNameSanitization:
    def test_nfkc_normalisation_applied(self) -> None:
        # Fullwidth letters NFKC-fold to ASCII.
        assert sanitize_display_name("ＡＢＣ") == "ABC"  # noqa: RUF001 — fullwidth on purpose
        # Surrounding whitespace is trimmed.
        assert sanitize_display_name("  Neo  ") == "Neo"

    def test_rejects_zero_width_chars(self) -> None:
        with pytest.raises(ValueError):
            sanitize_display_name("Ne​o")

    def test_rejects_bidi_override(self) -> None:
        with pytest.raises(ValueError):
            sanitize_display_name("user‮name")

    def test_rejects_control_chars(self) -> None:
        with pytest.raises(ValueError):
            sanitize_display_name("line1\nline2")

    def test_rejects_empty_after_trim(self) -> None:
        with pytest.raises(ValueError):
            sanitize_display_name("   ")

    async def test_register_rejects_zero_width_display_name(
        self, async_client: AsyncClient
    ) -> None:
        resp = await async_client.post(
            "/v1/auth/register",
            json={
                "email": "zw@example.com",
                "password": "SecurePass1",
                "display_name": "Evil‍Name",
            },
        )
        assert resp.status_code == 422

    async def test_register_rejects_bidi_display_name(self, async_client: AsyncClient) -> None:
        resp = await async_client.post(
            "/v1/auth/register",
            json={
                "email": "bidi@example.com",
                "password": "SecurePass1",
                "display_name": "spoof‮gnp.exe",
            },
        )
        assert resp.status_code == 422

    async def test_register_normalises_display_name(self, async_client: AsyncClient) -> None:
        resp = await async_client.post(
            "/v1/auth/register",
            json={
                "email": "fullwidth@example.com",
                "password": "SecurePass1",
                "display_name": "Ｎｅｏ",  # noqa: RUF001 — "Neo" fullwidth on purpose
            },
        )
        assert resp.status_code == 201
        me = await async_client.get(
            "/v1/auth/me",
            headers={"Authorization": f"Bearer {resp.json()['access_token']}"},
        )
        assert me.json()["display_name"] == "Neo"

    async def test_normal_registration_still_works(self, async_client: AsyncClient) -> None:
        resp = await async_client.post(
            "/v1/auth/register",
            json={
                "email": "ordinary@example.com",
                "password": "SecurePass1",
                "display_name": "Ordinary Gamer",
            },
        )
        assert resp.status_code == 201
