"""Curated blocklist of disposable / throwaway email providers.

Registrations from these domains are rejected (when ``block_disposable_emails``
is on) so the account base is not flooded with single-use, unreachable inboxes
that exist only to clear a verification gate once and never again.

The list is intentionally a plain ``frozenset`` of *lowercase* registrable
domains so it is trivial to extend (add a string) and O(1) to query. It is not
exhaustive — it covers the common, high-volume providers — and is meant to be
combined with the MX check and CAPTCHA, not to stand alone.
"""

from __future__ import annotations

# Lowercase registrable domains of well-known disposable mail providers. Many
# of these front dozens of rotating alias domains; we list the canonical ones
# and the most common aliases. Keep alphabetised for easy diffing/extension.
DISPOSABLE_EMAIL_DOMAINS: frozenset[str] = frozenset(
    {
        "0clock.net",
        "10minutemail.com",
        "10minutemail.net",
        "20minutemail.com",
        "33mail.com",
        "guerrillamail.biz",
        "guerrillamail.com",
        "guerrillamail.de",
        "guerrillamail.info",
        "guerrillamail.net",
        "guerrillamail.org",
        "guerrillamailblock.com",
        "sharklasers.com",
        "grr.la",
        "spam4.me",
        "mailinator.com",
        "mailinator.net",
        "mailinator2.com",
        "maildrop.cc",
        "tempmail.com",
        "temp-mail.org",
        "temp-mail.io",
        "tempmailo.com",
        "tempr.email",
        "throwawaymail.com",
        "throwawaymailbox.com",
        "yopmail.com",
        "yopmail.fr",
        "yopmail.net",
        "getnada.com",
        "nada.email",
        "trashmail.com",
        "trashmail.de",
        "trashmail.net",
        "trbvm.com",
        "dispostable.com",
        "fakeinbox.com",
        "fakemail.net",
        "discard.email",
        "discardmail.com",
        "emailondeck.com",
        "mailnesia.com",
        "mintemail.com",
        "mohmal.com",
        "mytemp.email",
        "spambox.us",
        "spamgourmet.com",
        "tempinbox.com",
        "tempmailaddress.com",
        "tmail.ws",
        "tmpmail.org",
        "wegwerfmail.de",
        "mailcatch.com",
        "moakt.com",
        "inboxbear.com",
        "burnermail.io",
    }
)


def is_disposable_domain(domain: str) -> bool:
    """Return ``True`` if *domain* (any case) is a known disposable provider.

    The comparison is done on the lowercased, whitespace-trimmed domain so the
    caller does not need to normalise first.
    """
    return domain.strip().lower() in DISPOSABLE_EMAIL_DOMAINS
