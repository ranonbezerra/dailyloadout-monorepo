"""Best-effort SMTP mailer infrastructure."""

from dailyloadout.infrastructure.email.mailer import (
    Mailer,
    get_mailer,
    send_verification_email,
)

__all__ = ["Mailer", "get_mailer", "send_verification_email"]
