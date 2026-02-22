"""
EmailSenderAdapter — Sends info-review emails via Resend.
Asks contacts to confirm or update the information we have on file.
"""

import asyncio
import logging
import os
from typing import TYPE_CHECKING, Optional

import resend

from ..domain.interfaces.i_email_sender_gateway import (
    IEmailSenderGateway,
    SendEmailResult,
)

if TYPE_CHECKING:
    from ..domain.entities.contact import Contact

logger = logging.getLogger(__name__)


class EmailSenderAdapter(IEmailSenderGateway):
    """
    Adapter that sends information-review emails using the Resend API.
    """

    def __init__(self, api_key: str = None, from_email: str = "rolodex@robbylinson.dev"):
        self.api_key = api_key or os.getenv("RESEND_API_KEY")
        self.from_email = from_email

        if self.api_key:
            resend.api_key = self.api_key

    async def send_confirmation(self, contact: "Contact") -> SendEmailResult:
        # Rate-limit: half-second delay between sends
        await asyncio.sleep(0.5)

        if not contact.email:
            return SendEmailResult(
                success=False,
                email=contact.email or "",
                error="No email address provided",
            )

        if not self.api_key:
            logger.warning(
                f"[EmailSender] RESEND_API_KEY not set. "
                f"Stubbing confirmation to {contact.name} <{contact.email}>"
            )
            return SendEmailResult(success=True, email=contact.email)

        first_name = contact.name.split()[0] if contact.name else "there"
        html_content = self._build_html(contact, first_name)

        try:
            logger.info(f"[EmailSender] Sending info-review email via Resend to {contact.email}")

            response = resend.Emails.send({
                "from": self.from_email,
                "to": [contact.email],
                "reply_to": "Rolodex-AI.r0xxak@zapiermail.com",
                "subject": "Please review the information we have on file for you",
                "html": html_content,
            })

            logger.info(
                f"[EmailSender] Successfully sent to {contact.email}. "
                f"Resend ID: {response.get('id')}"
            )
            return SendEmailResult(success=True, email=contact.email)

        except Exception as e:
            logger.error(f"[EmailSender] Failed to send to {contact.email}: {str(e)}")
            return SendEmailResult(
                success=False,
                email=contact.email,
                error=str(e),
            )

    # ── Private helpers ───────────────────────────────────────────────────

    @staticmethod
    def _build_html(contact: "Contact", first_name: str) -> str:
        def _row(label: str, value: Optional[str]) -> str:
            display = value if value else "<em>Not on file</em>"
            return (
                f'<tr style="border-bottom:1px solid #eee;">'
                f'<td style="padding:8px 12px;font-weight:600;color:#555;">{label}</td>'
                f'<td style="padding:8px 12px;">{display}</td>'
                f"</tr>"
            )

        rows = "".join([
            _row("Name", contact.name),
            _row("Email", contact.email),
            _row("Title", contact.title),
            _row("Organization", contact.organization),
            _row("District Website", contact.district_website),
            _row("LinkedIn URL", contact.linkedin_url),
        ])

        return f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;">
            <p>Hi {first_name},</p>
            <p>We are updating our district contact records. Below is the information
               we currently have on file for you:</p>
            <table style="width:100%;border-collapse:collapse;margin:16px 0;">
                {rows}
            </table>
            <p>If any of the above is out of date or incorrect, please reply to this
               email with the updated details. If everything looks good, no action is
               needed.</p>
            <p>Thank you for your time!</p>
            <p>Best,<br>ProspectKeeper Admin</p>
        </div>
        """
