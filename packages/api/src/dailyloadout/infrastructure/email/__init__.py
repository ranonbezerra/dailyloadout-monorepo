"""Best-effort SMTP mailer + registration email-quality checks."""

from dailyloadout.infrastructure.email.mailer import (
    Mailer,
    get_mailer,
    send_verification_email,
)
from dailyloadout.infrastructure.email.validation import (
    domain_has_mail_records,
    is_disposable_email,
)

__all__ = [
    "Mailer",
    "domain_has_mail_records",
    "get_mailer",
    "is_disposable_email",
    "send_verification_email",
]
