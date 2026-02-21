"""
CamoUFoxAdapter - Implements ILinkedInGateway.
Tier 2: Headless LinkedIn verification using CamoUFox (anti-detection browser).
CamoUFox is a hardened Firefox that mimics human behavior to bypass bot detection.
Cost: $0.00 (local compute only)
"""

import asyncio
import logging
import os
import re
from typing import Optional

from ..domain.interfaces.i_linkedin_gateway import ILinkedInGateway, LinkedInResult

logger = logging.getLogger(__name__)

LINKEDIN_TIMEOUT_SECONDS = 15


class CamoUFoxAdapter(ILinkedInGateway):
    """
    Tier 2 LinkedIn verification via CamoUFox headless browser.

    Requires CamoUFox to be installed: pip install camoufox[geoip]
    And Playwright: playwright install firefox

    Falls back gracefully if CamoUFox is unavailable.
    """

    async def verify_employment(
        self,
        contact_name: str,
        organization: str,
        linkedin_url: Optional[str] = None,
    ) -> LinkedInResult:
        try:
            return await asyncio.wait_for(
                self._scrape_linkedin(contact_name, organization, linkedin_url),
                timeout=LINKEDIN_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.warning(f"[Tier2] LinkedIn timeout for {contact_name}")
            return LinkedInResult(success=False, error="Timeout", blocked=False)
        except ImportError:
            logger.warning("[Tier2] CamoUFox not installed — skipping LinkedIn tier")
            return LinkedInResult(
                success=False,
                error="CamoUFox not installed",
                blocked=False,
            )
        except Exception as e:
            logger.warning(f"[Tier2] LinkedIn error for {contact_name}: {e}")
            return LinkedInResult(success=False, error=str(e))

    async def _scrape_linkedin(
        self,
        contact_name: str,
        organization: str,
        linkedin_url: Optional[str],
    ) -> LinkedInResult:
        """
        Actual CamoUFox scraping logic.
        Uses async_playwright context managed by CamoUFox for fingerprint evasion.
        """
        from camoufox.async_api import AsyncCamoufox

        async with AsyncCamoufox(headless=False) as browser:
            page = await browser.new_page()

            # Inject LinkedIn auth cookies if available
            li_at_cookie = os.environ.get("LINKEDIN_LI_AT")
            cookies_string = os.environ.get("LINKEDIN_COOKIES_STRING")
            
            cookies_to_add = []
            
            if cookies_string:
                cookie_parts = cookies_string.split(";")
                for part in cookie_parts:
                    if "=" in part:
                        name, value = part.strip().split("=", 1)
                        cookies_to_add.append({
                            "name": name.strip(),
                            "value": value.strip(' "'),
                            "domain": ".linkedin.com",
                            "path": "/",
                            "secure": True,
                        })
            elif li_at_cookie:
                cookies_to_add.append({
                    "name": "li_at",
                    "value": li_at_cookie,
                    "domain": ".linkedin.com",
                    "path": "/",
                    "secure": True,
                })
                
            if cookies_to_add:
                await page.context.add_cookies(cookies_to_add)

            # Determine URL to visit
            target_url = linkedin_url
            if not target_url:
                # Use LinkedIn people search
                target_url = (
                    f"https://www.linkedin.com/search/results/people/"
                    f"?keywords={contact_name.replace(' ', '%20')}%20{organization.replace(' ', '%20')}"
                )

            await page.goto(target_url, wait_until="networkidle")
            
            # Wait for the main profile section or just wait a few seconds for React to render
            try:
                await page.wait_for_timeout(3000)
            except:
                pass

            # Check if LinkedIn blocked us
            if "authwall" in page.url or "checkpoint" in page.url or "login" in page.url:
                logger.warning("[Tier2] LinkedIn auth wall hit")
                await page.screenshot(path="debug_linkedin.png")
                return LinkedInResult(success=False, blocked=True, error="Auth wall")

            # Parse current position from profile page
            await page.screenshot(path="debug_linkedin.png")
            page_text = await page.inner_text("body")
            return self._parse_linkedin_page(
                page_text, contact_name, organization, page.url
            )

    def _parse_linkedin_page(
        self,
        text: str,
        _contact_name: str,
        organization: str,
        profile_url: str,
    ) -> LinkedInResult:
        """Parse LinkedIn page text to determine current employment."""
        text_lower = text.lower()
        org_lower = organization.lower()
        # Simple heuristic: check if organization name appears in "current" context
        still_there = org_lower in text_lower

        # Try to extract current title from common patterns
        title_match = re.search(
            r"(Director|Manager|VP|Head of|Chief|Lead|President)[^\n]{0,60}",
            text,
            re.IGNORECASE,
        )
        current_title = title_match.group(0).strip() if title_match else None

        return LinkedInResult(
            success=True,
            still_at_organization=still_there,
            current_title=current_title,
            current_organization=organization if still_there else None,
            profile_url=profile_url,
        )
