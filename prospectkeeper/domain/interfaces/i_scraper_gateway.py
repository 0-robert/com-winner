"""
IScraperGateway - Port: Tier 1 web scraping interface.
Implementations use BeautifulSoup / HTTPX against public district websites.
Cost: $0.00
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ScraperResult:
    success: bool
    person_found: bool = False
    current_title: Optional[str] = None
    organization: Optional[str] = None
    evidence_url: Optional[str] = None
    raw_text: Optional[str] = None
    error: Optional[str] = None


class IScraperGateway(ABC):
    """Port for scraping public district websites (Tier 1 — free)."""

    @abstractmethod
    async def find_contact_on_district_site(
        self,
        contact_name: str,
        organization: str,
        district_website: Optional[str] = None,
    ) -> ScraperResult:
        """
        Attempts to find the contact on the district's public staff directory.
        Returns a ScraperResult indicating whether the contact is still listed.
        """
        pass
