"""Common-password blocklist — a lightweight, offline breached-password check.

NIST 800-63B recommends rejecting passwords known to be compromised. A full check
queries a breach corpus (e.g. HIBP's k-anonymity range API); to stay offline and
dependency-free, this bundles a curated list of the most common passwords, focused
on the ones that *pass* the complexity rules (``Password1``, ``Qwerty123``,
``Welcome2024``, …) and so would otherwise slip through.

A true HIBP check is the future upgrade: it's an **async** call, so it belongs
behind a port in the service layer, not in the sync schema validator that calls
``is_common_password`` today.
"""

from __future__ import annotations

from pathlib import Path

_DATA = Path(__file__).parent / "data" / "common_passwords.txt"


def _load() -> frozenset[str]:
    lines = _DATA.read_text(encoding="utf-8").splitlines()
    return frozenset(s.lower() for line in lines if (s := line.strip()) and not s.startswith("#"))


_COMMON = _load()


def is_common_password(password: str) -> bool:
    """True if *password* is on the common-password blocklist (case-insensitive)."""
    return password.strip().lower() in _COMMON
