"""
IEmailSenderGateway - Port: send confirmation emails to contacts.
Used by the Free tier to ask contacts "Are you still reachable at ___?"
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class SendEmailResult:
    success: bool
    email: str
    error: Optional[str] = None


class IEmailSenderGateway(ABC):
    """Port for sending confirmation emails (Free tier)."""

    @abstractmethod
    async def send_confirmation(self, email: str, name: str) -> SendEmailResult:
        """
        Sends a confirmation email to the contact asking:
        'Are you still reachable at {email}?'
        Returns whether the send was successful.
        """
        pass
