"""
IAIGateway - Port: Tier 3 AI research interface.
Implementations call Claude via Helicone proxy for deep web research.
Cost: ~$0.01 per contact (token-based)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AIResearchResult:
    success: bool
    contact_still_active: Optional[bool] = None
    current_title: Optional[str] = None
    current_organization: Optional[str] = None

    # Replacement contact (if original is gone)
    replacement_name: Optional[str] = None
    replacement_title: Optional[str] = None
    replacement_email: Optional[str] = None

    # Telemetry (tracked by Helicone)
    tokens_input: int = 0
    tokens_output: int = 0
    cost_usd: float = 0.0
    evidence_urls: List[str] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def total_tokens(self) -> int:
        return self.tokens_input + self.tokens_output


class IAIGateway(ABC):
    """Port for deep AI-powered contact research (Tier 3 — Claude via Helicone)."""

    @abstractmethod
    async def research_contact(
        self,
        contact_name: str,
        organization: str,
        title: str,
        context_text: Optional[str] = None,
    ) -> AIResearchResult:
        """
        Uses Claude to research whether the contact is still in their role
        and identifies a replacement contact if they have departed.
        All calls are traced through Helicone for cost-per-contact observability.
        """
        pass
