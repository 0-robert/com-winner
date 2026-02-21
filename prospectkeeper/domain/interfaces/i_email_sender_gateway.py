"""
IEmailSenderGateway - Port: send confirmation emails to contacts.
Used by the Free tier to ask contacts to review their information on file.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..entities.contact import Contact


@dataclass
class SendEmailResult:
    success: bool
    email: str
    error: Optional[str] = None


class IEmailSenderGateway(ABC):
    """Port for sending confirmation emails (Free tier)."""

    @abstractmethod
    async def send_confirmation(self, contact: "Contact") -> SendEmailResult:
        """
        Sends an email to the contact listing the information we have on file
        and requesting any updates or corrections.
        Returns whether the send was successful.
        """
        pass
