"""
IEmailVerificationGateway - Port: Tier 1 email validation interface.
Implementations call ZeroBounce REST API.
Cost: ~$0.004 per email (ZeroBounce credits)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class EmailStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    CATCH_ALL = "catch-all"
    UNKNOWN = "unknown"
    SPAMTRAP = "spamtrap"
    ABUSE = "abuse"
    DO_NOT_MAIL = "do-not-mail"


@dataclass
class EmailVerificationResult:
    email: str
    status: EmailStatus
    deliverability: str  # "Deliverable", "Undeliverable", "Risky"
    is_valid: bool
    cost_usd: float = 0.004  # ZeroBounce per-credit cost
    sub_status: Optional[str] = None
    error: Optional[str] = None


class IEmailVerificationGateway(ABC):
    """Port for email deliverability validation (Tier 1 — ZeroBounce)."""

    @abstractmethod
    async def verify_email(self, email: str) -> EmailVerificationResult:
        """
        Validates email deliverability via ZeroBounce API.
        Returns the validation status and deliverability score.
        """
        pass
