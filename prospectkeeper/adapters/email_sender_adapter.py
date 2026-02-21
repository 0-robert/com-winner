"""
EmailSenderAdapter — Stub implementation of IEmailSenderGateway.
Logs the confirmation email instead of actually sending it.
Replace with a real SMTP implementation when ready for production.
"""

import logging
import os
import resend

from ..domain.interfaces.i_email_sender_gateway import (
    IEmailSenderGateway,
    SendEmailResult,
)

logger = logging.getLogger(__name__)


class EmailSenderAdapter(IEmailSenderGateway):
    """
    Adapter that sends confirmation emails using the Resend API.
    """

    def __init__(self, api_key: str = None, from_email: str = "onboarding@resend.dev"):
        self.api_key = api_key or os.getenv("RESEND_API_KEY")
        self.from_email = from_email
        
        if self.api_key:
            resend.api_key = self.api_key

    async def send_confirmation(self, email: str, name: str) -> SendEmailResult:
        if not email:
            return SendEmailResult(
                success=False,
                email=email,
                error="No email address provided",
            )
            
        if not self.api_key:
            logger.warning(
                f"[EmailSender] RESEND_API_KEY not set. Stubbing confirmation to {name} <{email}>"
            )
            return SendEmailResult(success=True, email=email)

        first_name = name.split()[0] if name else "there"
        
        html_content = f"""
        <p>Hi {first_name},</p>
        <p>Are you still reachable at this email address? We are updating our district contact records.</p>
        <p>Best,<br>ProspectKeeper Admin</p>
        """

        try:
            logger.info(f"[EmailSender] Sending confirmation via Resend to {email}")
            
            # Note: The free Resend tier can only send TO the email address you verify 
            # in their dashboard (usually your own email), unless you add a domain.
            response = resend.Emails.send({
                "from": self.from_email,
                "to": [email],
                "subject": "Are you still reachable at this email?",
                "html": html_content
            })
            
            logger.info(f"[EmailSender] Successfully sent to {email}. Resend ID: {response.get('id')}")
            return SendEmailResult(success=True, email=email)
            
        except Exception as e:
            logger.error(f"[EmailSender] Failed to send to {email}: {str(e)}")
            return SendEmailResult(
                success=False, 
                email=email,
                error=str(e)
            )
