"""Deliverability / quality checks applied to a registration email.

Two independent, config-toggled guards:

* :func:`is_disposable_email` — static blocklist lookup (cheap, deterministic).
* :func:`domain_has_mail_records` — best-effort MX/A DNS probe that **fails
  OPEN**: any lookup error or timeout ALLOWS the address (a DNS hiccup must
  never lock out a legitimate user). Only a definitive "this domain publishes
  no mail records" returns ``False``.

Both operate purely on the email DOMAIN, so neither can be used as an
account-existence oracle (the verdict is identical whether or not the address
is already registered).
"""

from __future__ import annotations

import asyncio

import dns.exception
import dns.resolver
import structlog

from slate.config import settings
from slate.infrastructure.config.dynamic import dynamic_config
from slate.infrastructure.email.disposable_domains import is_disposable_domain

logger = structlog.get_logger()


class EmailRejectedError(ValueError):
    """Email rejected on quality grounds (disposable / undeliverable domain).

    Distinct from a duplicate-email conflict so the router can return 422
    (invalid input) rather than 409. The verdict is domain-based, so it leaks
    no account-existence signal.
    """


async def assert_email_acceptable(email: str) -> None:
    """Reject disposable domains and (best-effort) undeliverable ones.

    Order: cheap static blocklist first, then the network MX probe. The MX
    probe is skipped outside production (CI/dev do no DNS) and fails OPEN — only
    a definitive "no mail records" rejects. Both checks are domain-based, so
    neither is an account-existence oracle.
    """
    domain = _extract_domain(email)
    if await dynamic_config.get_bool("block_disposable_emails") and is_disposable_email(email):
        logger.warning("email_rejected", reason="disposable_domain", domain=domain)
        raise EmailRejectedError("Disposable email addresses are not allowed.")

    mx_enabled = settings.check_email_mx and settings.is_production
    if mx_enabled and not await domain_has_mail_records(email):
        logger.warning("email_rejected", reason="undeliverable_domain", domain=domain)
        raise EmailRejectedError("Email domain cannot receive mail.")


def _extract_domain(email: str) -> str:
    """Return the lowercased domain part of *email* (empty if malformed)."""
    local, sep, domain = email.rpartition("@")
    if not sep or not local:
        return ""
    return domain.strip().lower().rstrip(".")


def is_disposable_email(email: str) -> bool:
    """Return ``True`` when *email*'s domain is a known disposable provider."""
    domain = _extract_domain(email)
    if not domain:
        return False
    return is_disposable_domain(domain)


def _domain_resolves_mail(domain: str) -> bool:
    """Blocking DNS probe: does *domain* publish an MX (or fallback A/AAAA)?

    Returns:
        ``True``  — the domain has MX records, or (no MX) an A/AAAA record, or
                    the lookup was inconclusive (errors → fail OPEN).
        ``False`` — the domain definitively resolves but publishes no MX **and**
                    no A/AAAA record, i.e. mail is undeliverable.
    """
    resolver = dns.resolver.Resolver()
    # Short, bounded budget so a slow nameserver can't stall the request; on
    # timeout we fall through to the fail-open path below.
    resolver.timeout = settings.email_mx_timeout_seconds
    resolver.lifetime = settings.email_mx_timeout_seconds

    try:
        answers = resolver.resolve(domain, "MX")
        if len(answers) > 0:
            return True
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        # No MX (or domain absent): fall back to an A/AAAA record — RFC 5321
        # treats an address record as an implicit mail destination.
        return _domain_has_address_record(resolver, domain)
    except (dns.exception.Timeout, dns.resolver.NoNameservers, dns.exception.DNSException):
        # Resolver trouble (timeout, all nameservers failed, etc.) — FAIL OPEN.
        logger.info("email_mx_check_inconclusive", domain=domain, exc_info=True)
        return True
    return True


def _domain_has_address_record(resolver: dns.resolver.Resolver, domain: str) -> bool:
    """Best-effort A/AAAA fallback used when a domain has no MX records."""
    for record_type in ("A", "AAAA"):
        try:
            answers = resolver.resolve(domain, record_type)
            if len(answers) > 0:
                return True
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            continue
        except dns.exception.DNSException:
            # Inconclusive — fail OPEN rather than block a real user.
            return True
    return False


async def domain_has_mail_records(email: str) -> bool:
    """Async, non-blocking, fail-open MX/A check for *email*'s domain.

    Runs the blocking resolver in a worker thread so the event loop is never
    stalled. A missing/garbage domain part returns ``True`` (fail open — the
    syntactic ``EmailStr`` check is the authority on shape, not this probe).
    """
    domain = _extract_domain(email)
    if not domain:
        return True
    try:
        return await asyncio.to_thread(_domain_resolves_mail, domain)
    except Exception:  # pragma: no cover - defensive; thread errors fail open
        logger.warning("email_mx_check_errored", domain=domain, exc_info=True)
        return True
