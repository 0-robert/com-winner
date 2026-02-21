"""
Contact Entity - Core domain object.
No framework dependencies. Business logic lives here.
"""

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime
import uuid


class ContactStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNKNOWN = "unknown"
    OPTED_OUT = "opted_out"


@dataclass
class Contact:
    """
    Core entity representing a B2B contact (Special Education Director).
    Encapsulates identity, current status, and domain behaviour.
    """

    id: str
    name: str
    email: str
    title: str
    organization: str
    status: ContactStatus = ContactStatus.UNKNOWN
    needs_human_review: bool = False
    review_reason: Optional[str] = None
    district_website: Optional[str] = None
    linkedin_url: Optional[str] = None
    email_hash: Optional[str] = None  # For anonymization after opt-out
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(
        cls,
        name: str,
        email: str,
        title: str,
        organization: str,
        district_website: Optional[str] = None,
        linkedin_url: Optional[str] = None,
    ) -> "Contact":
        """Factory method to create a new Contact with a generated ID."""
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            email=email,
            title=title,
            organization=organization,
            district_website=district_website,
            linkedin_url=linkedin_url,
        )

    def flag_for_review(self, reason: str) -> None:
        """Mark this contact for human review with a reason."""
        self.needs_human_review = True
        self.review_reason = reason
        self.updated_at = datetime.utcnow()

    def clear_review_flag(self) -> None:
        """Clear the human review flag once resolved."""
        self.needs_human_review = False
        self.review_reason = None
        self.updated_at = datetime.utcnow()

    def update_email(self, new_email: str) -> None:
        """Update the contact's email after verification."""
        self.email = new_email
        self.updated_at = datetime.utcnow()

    def mark_active(self) -> None:
        """Confirm this contact is still in their role."""
        self.status = ContactStatus.ACTIVE
        self.updated_at = datetime.utcnow()

    def mark_inactive(self) -> None:
        """Mark that the contact has left their position."""
        self.status = ContactStatus.INACTIVE
        self.updated_at = datetime.utcnow()

    def opt_out(self) -> None:
        """
        GDPR/CCPA compliance: anonymize PII and halt all tracking.
        Retains an email hash for deduplication purposes only.
        """
        self.email_hash = hashlib.sha256(self.email.lower().encode()).hexdigest()
        self.name = "[OPTED OUT]"
        self.email = ""
        self.title = ""
        self.organization = ""
        self.district_website = None
        self.linkedin_url = None
        self.status = ContactStatus.OPTED_OUT
        self.needs_human_review = False
        self.updated_at = datetime.utcnow()

    def is_opted_out(self) -> bool:
        return self.status == ContactStatus.OPTED_OUT
