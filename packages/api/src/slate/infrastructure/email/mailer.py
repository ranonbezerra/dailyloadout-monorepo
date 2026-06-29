"""Best-effort, config-driven SMTP mailer.

Sending is *never* allowed to break a request: if ``smtp_host`` is not
configured the mailer logs and skips, and any SMTP error is caught and logged
rather than propagated. This keeps registration working in dev (no SMTP) and
resilient in prod (transient SMTP outage) while still delivering verification
mail when the server is reachable.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

import structlog

from slate.config import settings

logger = structlog.get_logger()


class Mailer:
    """Thin wrapper over ``smtplib`` driven entirely by ``settings``."""

    def __init__(self) -> None:
        self._host = settings.smtp_host
        self._port = settings.smtp_port
        self._user = settings.smtp_user
        self._password = settings.smtp_password
        self._from = settings.smtp_from

    @property
    def configured(self) -> bool:
        """True only when an SMTP host is set (otherwise mail is skipped)."""
        return bool(self._host)

    def send(self, *, to: str, subject: str, body: str) -> bool:
        """Send a plain-text email. Returns ``True`` if it was sent.

        Best-effort: when SMTP is not configured, or sending fails for any
        reason, this logs and returns ``False`` without raising.
        """
        if not self.configured:
            logger.info("mailer_skip_unconfigured", to=to, subject=subject)
            return False

        message = EmailMessage()
        message["From"] = self._from
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)

        try:
            self._deliver(message)
        except Exception:
            logger.warning("mailer_send_failed", to=to, subject=subject, exc_info=True)
            return False

        logger.info("mailer_sent", to=to, subject=subject)
        return True

    def _deliver(self, message: EmailMessage) -> None:
        """Open an SMTP connection, STARTTLS, optional login, and send."""
        with smtplib.SMTP(self._host, self._port, timeout=10) as client:
            client.starttls()
            if self._user:
                client.login(self._user, self._password)
            client.send_message(message)


def get_mailer() -> Mailer:
    """Provide a ``Mailer`` (FastAPI dependency / service helper)."""
    return Mailer()


def send_verification_email(mailer: Mailer, *, to: str, token: str) -> bool:
    """Compose and best-effort-send an email-verification message."""
    link = f"{settings.email_verification_base_url}?token={token}"
    body = (
        "Welcome to Slate!\n\n"
        "Please verify your email address by opening this link:\n\n"
        f"{link}\n\n"
        "If you did not create this account, you can ignore this message."
    )
    return mailer.send(to=to, subject="Verify your Slate email", body=body)


def send_password_reset_email(mailer: Mailer, *, to: str, token: str) -> bool:
    """Compose and best-effort-send a password-reset link."""
    link = f"{settings.password_reset_base_url}?token={token}"
    body = (
        "We received a request to reset your Slate password.\n\n"
        "Open this link to choose a new password:\n\n"
        f"{link}\n\n"
        "This link expires soon. If you did not request a reset, you can safely "
        "ignore this message — your password will not change."
    )
    return mailer.send(to=to, subject="Reset your Slate password", body=body)


def send_password_changed_email(mailer: Mailer, *, to: str) -> bool:
    """Send a security notice that the account password was changed."""
    body = (
        "Your Slate password was just changed.\n\n"
        "If this was you, no action is needed. If you did NOT make this change, "
        "your account may be compromised: reset your password immediately and "
        "review your active sessions."
    )
    return mailer.send(to=to, subject="Your Slate password was changed", body=body)
