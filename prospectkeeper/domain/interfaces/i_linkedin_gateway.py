"""
ILinkedInGateway - Port: Tier 2 LinkedIn verification interface.
Implementations use CamoUFox (headless browser) for anti-detection scraping.
Cost: $0.00 (local compute only)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class LinkedInResult:
    success: bool
    still_at_organization: Optional[bool] = None
    current_title: Optional[str] = None
    current_organization: Optional[str] = None
    profile_url: Optional[str] = None
    error: Optional[str] = None
    blocked: bool = False  # True if LinkedIn blocked the request
    # Extended profile fields (populated by NoDriverAdapter)
    name: Optional[str] = None
    headline: Optional[str] = None
    location: Optional[str] = None
    experience: Optional[list] = None  # list of {title, company, dateRange, isCurrent, description}
    education: Optional[list] = None   # list of {institution, degree, dateRange}
    skills: Optional[list] = None      # list of skill name strings


class ILinkedInGateway(ABC):
    """Port for LinkedIn employment verification (Tier 2 — local compute)."""

    @abstractmethod
    async def verify_employment(
        self,
        contact_name: str,
        organization: str,
        linkedin_url: Optional[str] = None,
    ) -> LinkedInResult:
        """
        Attempts to verify current employment via LinkedIn profile scraping.
        Uses CamoUFox to avoid bot detection.
        """
        pass
