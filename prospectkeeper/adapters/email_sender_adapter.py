"""
EmailSenderAdapter — Stub implementation of IEmailSenderGateway.
Logs the confirmation email instead of actually sending it.
Replace with a real SMTP implementation when ready for production.
"""

import logging
from ..domain.interfaces.i_email_sender_gateway import (
    IEmailSenderGateway,
    SendEmailResult,
)

logger = logging.getLogger(__name__)


class EmailSenderAdapter(IEmailSenderGateway):
    """
    Stub adapter that logs confirmation emails.
    In production, replace with SMTP / SendGrid / SES implementation.
    """

    async def send_confirmation(self, email: str, name: str) -> SendEmailResult:
        if not email:
            return SendEmailResult(
                success=False,
                email=email,
                error="No email address provided",
            )

        logger.info(
            f"[EmailSender] Sending confirmation to {name} <{email}>: "
            f"'Are you still reachable at {email}?'"
        )

        # Stub: always succeed
        return SendEmailResult(success=True, email=email)
