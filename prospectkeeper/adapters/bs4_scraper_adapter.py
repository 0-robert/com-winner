"""
BS4ScraperAdapter - Implements IScraperGateway.
Tier 1: Free scraping of public district websites using httpx + BeautifulSoup.
Enforces strict timeouts (10s) — abandons on timeout to stay cost-efficient.
"""

import asyncio
import logging
import re
from typing import Optional
from urllib.parse import quote_plus, urljoin

import httpx
from bs4 import BeautifulSoup

from ..domain.interfaces.i_scraper_gateway import IScraperGateway, ScraperResult

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 10
USER_AGENT = (
    "Mozilla/5.0 (compatible; ProspectKeeper/1.0; +https://prospectkeeper.ai)"
)

# Patterns to detect "special education director" type pages
TITLE_KEYWORDS = [
    "director",
    "manager",
    "head of",
    "vp",
    "vice president",
    "chief",
    "lead",
]


class BS4ScraperAdapter(IScraperGateway):
    """
    Tier 1 scraper using BeautifulSoup.
    Strategy:
    1. Try the district website's staff directory if URL known.
    2. Fall back to a Google search URL pattern as a hint (no actual Google scraping).
    Cost: $0.00
    """

    async def find_contact_on_district_site(
        self,
        contact_name: str,
        organization: str,
        district_website: Optional[str] = None,
    ) -> ScraperResult:
        if not district_website:
            logger.info(
                f"[Tier1] No district website for {organization} — skipping"
            )
            return ScraperResult(success=False, error="No district website provided")

        try:
            async with httpx.AsyncClient(
                timeout=TIMEOUT_SECONDS,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
            ) as client:
                # Try the staff directory page
                staff_url = await self._guess_staff_url(client, district_website)
                if not staff_url:
                    return ScraperResult(
                        success=False,
                        error=f"Could not locate staff directory at {district_website}",
                    )


                response = await client.get(staff_url)
                response.raise_for_status()

                return self._parse_staff_page(
                    response.text, contact_name, staff_url
                )

        except httpx.TimeoutException:
            logger.warning(f"[Tier1] Timeout scraping {district_website}")
            return ScraperResult(success=False, error="Timeout")
        except Exception as e:
            logger.warning(f"[Tier1] Error scraping {district_website}: {e}")
            return ScraperResult(success=False, error=str(e))

    async def _guess_staff_url(
        self, client: httpx.AsyncClient, base_url: str
    ) -> Optional[str]:
        """Attempt to find a staff/administration page by checking common URL patterns."""
        candidates = [
            f"{base_url.rstrip('/')}/team",
            f"{base_url.rstrip('/')}/staff",
            f"{base_url.rstrip('/')}/our-team",
            f"{base_url.rstrip('/')}/about/team",
            f"{base_url.rstrip('/')}/about-us",
            f"{base_url.rstrip('/')}/company/team",
            f"{base_url.rstrip('/')}/people",
            f"{base_url.rstrip('/')}/leadership",
        ]
        for url in candidates:
            try:
                resp = await client.get(url, timeout=5)
                if resp.status_code == 200:
                    return url
            except Exception:
                continue
        return None

    def _parse_staff_page(
        self, html: str, contact_name: str, page_url: str
    ) -> ScraperResult:
        """Parse HTML to find if the contact name appears on the page."""
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" ", strip=True).lower()

        name_lower = contact_name.lower()
        # Check if the name appears on the page
        if name_lower not in text:
            # Name not found — might have left
            return ScraperResult(
                success=True,
                person_found=False,
                evidence_url=page_url,
                raw_text=text[:500],
            )

        # Name found — try to extract their current title from surrounding context
        idx = text.find(name_lower)
        context = text[max(0, idx - 100) : idx + 200]

        title = None
        for keyword in TITLE_KEYWORDS:
            if keyword in context:
                title = keyword.title()
                break

        return ScraperResult(
            success=True,
            person_found=True,
            current_title=title,
            evidence_url=page_url,
            raw_text=context,
        )
