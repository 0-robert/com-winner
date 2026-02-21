"""
VerificationResult - Output of the VerifyContactUseCase.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from .contact import ContactStatus
from .agent_economics import AgentEconomics


@dataclass
class VerificationResult:
    """
    Encapsulates the outcome of verifying a single contact,
    along with the economic cost of that verification.
    """

    contact_id: str
    status: ContactStatus
    economics: AgentEconomics

    # Replacement data (populated when status=INACTIVE and a new contact is found)
    replacement_name: Optional[str] = None
    replacement_email: Optional[str] = None
    replacement_title: Optional[str] = None

    # Confidence & evidence
    low_confidence_flag: bool = False
    current_organization: Optional[str] = None
    evidence_urls: List[str] = field(default_factory=list)
    notes: Optional[str] = None

    @property
    def has_replacement(self) -> bool:
        return self.replacement_name is not None and self.replacement_email is not None

    @property
    def needs_human_review(self) -> bool:
        return self.low_confidence_flag or self.status == ContactStatus.UNKNOWN
