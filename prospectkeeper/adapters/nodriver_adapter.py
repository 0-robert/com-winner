"""
NoDriverAdapter - Implements ILinkedInGateway.
Tier 2: Headless LinkedIn verification using nodriver.
nodriver is a modern asynchronous undetectable browser automation framework.
"""

import asyncio
import json
import logging
import os
import re
from typing import Optional

from bs4 import BeautifulSoup

from ..domain.interfaces.i_linkedin_gateway import ILinkedInGateway, LinkedInResult

logger = logging.getLogger(__name__)

LINKEDIN_TIMEOUT_SECONDS = 60


class NoDriverAdapter(ILinkedInGateway):
    """
    Tier 2 LinkedIn verification via nodriver browser.

    Requires: pip install nodriver beautifulsoup4
    Optional: place a JSON cookie export as linkedincookie.json in the project root
              (or set LINKEDIN_COOKIES_FILE env var) for authenticated access.
              Falls back to LINKEDIN_COOKIES_STRING (semicolon-separated name=value pairs).

    Architecture: browser is used only to load pages and capture raw HTML.
    All parsing is done in Python with BeautifulSoup — no complex JS evaluation
    that can fail due to CDP context invalidation from LinkedIn's SPA routing.
    """

    async def verify_employment(
        self,
        contact_name: str,
        organization: str,
        linkedin_url: Optional[str] = None,
    ) -> LinkedInResult:
        if not linkedin_url:
            logger.info(f"[Tier2] No LinkedIn URL stored for {contact_name} — skipping tier")
            return LinkedInResult(success=False, error="No LinkedIn URL stored", blocked=False)

        try:
            return await asyncio.wait_for(
                self._scrape_linkedin(contact_name, organization, linkedin_url),
                timeout=LINKEDIN_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.warning(f"[Tier2] LinkedIn timeout for {contact_name}")
            return LinkedInResult(success=False, error="Timeout", blocked=False)
        except ImportError:
            logger.warning("[Tier2] nodriver not installed — skipping LinkedIn tier")
            return LinkedInResult(success=False, error="nodriver not installed", blocked=False)
        except Exception as e:
            logger.warning(f"[Tier2] LinkedIn error for {contact_name}: {e}")
            return LinkedInResult(success=False, error=str(e))

    async def _scrape_linkedin(
        self,
        contact_name: str,
        organization: str,
        linkedin_url: str,
    ) -> LinkedInResult:
        import nodriver as uc

        browser = await uc.start(headless=False)
        try:
            # ── 1. Inject cookies ─────────────────────────────────────────────
            page = await browser.get("https://www.linkedin.com/")
            await page.sleep(1.5)
            cookies = self._build_cookies(uc)
            if cookies:
                await page.send(uc.cdp.network.set_cookies(cookies=cookies))
                logger.debug(f"[Tier2] Injected {len(cookies)} cookies")

            # ── 2. Navigate to profile ────────────────────────────────────────
            page = await browser.get(linkedin_url)
            try:
                await page.wait_for(selector="h1", timeout=12)
            except asyncio.TimeoutError:
                logger.warning(f"[Tier2] h1 not found for {contact_name}")

            # ── 3. Auth-wall check ────────────────────────────────────────────
            current_url = page.target.url
            if any(kw in current_url for kw in ("authwall", "checkpoint", "login", "uas/authenticate")):
                logger.warning("[Tier2] Auth wall detected")
                await page.save_screenshot("debug_linkedin_authwall.png")
                return LinkedInResult(success=False, blocked=True, error="Auth wall")

            # ── 4. Get main profile HTML (with retry on CDP context errors) ───
            await page.sleep(2)
            await page.save_screenshot("debug_linkedin.png")
            html = await self._get_html(page)
            if not html:
                return LinkedInResult(
                    success=False, error="Failed to capture page HTML", profile_url=current_url
                )

            with open("debug_linkedin.html", "w", encoding="utf-8") as f:
                f.write(html)
            logger.debug(f"[Tier2] Main profile HTML: {len(html):,} bytes")

            # ── 5. Parse main profile ─────────────────────────────────────────
            soup = BeautifulSoup(html, "html.parser")
            profile = self._parse_main_profile(soup)

            # ── 6. Fetch detail pages for complete education + skills ──────────
            detail_links = profile.pop("detailLinks", {})
            profile["education"], profile["skills"] = await self._fetch_detail_pages(
                browser, detail_links,
                education=profile.get("education", []),
                skills=profile.get("skills", []),
            )

            logger.debug(
                f"[Tier2] name={profile.get('name')!r} "
                f"exp={len(profile.get('experience', []))} "
                f"edu={len(profile.get('education', []))} "
                f"skills={len(profile.get('skills', []))}"
            )

            return self._build_result(profile, contact_name, organization, current_url)

        finally:
            browser.stop()

    # ── HTML capture ──────────────────────────────────────────────────────────

    @staticmethod
    async def _get_html(page, retries: int = 3) -> str:
        """Get page HTML via CDP, retrying on context-invalidation errors."""
        for attempt in range(retries):
            try:
                html = await page.evaluate("document.body.outerHTML", return_by_value=True)
                return html or ""
            except Exception as e:
                if attempt < retries - 1:
                    logger.debug(f"[Tier2] HTML capture attempt {attempt + 1} failed: {e} — retrying")
                    await asyncio.sleep(1.5)
                else:
                    logger.warning(f"[Tier2] HTML capture failed after {retries} attempts: {e}")
                    return ""

    # ── BeautifulSoup parsing ─────────────────────────────────────────────────

    @staticmethod
    def _parse_main_profile(soup: BeautifulSoup) -> dict:
        """
        Extract all profile data from the main profile page HTML.

        DOM structure (verified Feb 2025):
          Name:       h1.t-24.v-align-middle.break-words
          Headline:   div.text-body-medium.break-words[data-generated-suggestion-target]
          Location:   span.text-body-small.t-black--light.break-words
          Sections:   <section> containing <div id="experience|education|skills">
          Entries:    li.artdeco-list__item within each section
          Title:      div.hoverable-link-text.t-bold span[aria-hidden=true]
          Company:    span.t-14.t-normal:not(.t-black--light) span[aria-hidden=true]
          Date:       span.pvs-entity__caption-wrapper[aria-hidden=true]
          Desc:       div[class*=inline-show-more-text] span[aria-hidden=true]
        """
        def txt(root, sel):
            el = root.select_one(sel)
            return el.get_text(strip=True) if el else ""

        # ── Top card ──────────────────────────────────────────────────────────
        name = txt(soup, "h1.t-24.v-align-middle.break-words")
        headline = txt(soup, "div.text-body-medium.break-words[data-generated-suggestion-target]")
        location = txt(soup, "span.text-body-small.t-black--light.break-words")

        # ── Section helper ────────────────────────────────────────────────────
        def get_section(section_id):
            anchor = soup.find("div", id=section_id)
            return anchor.find_parent("section") if anchor else None

        # ── Experience ────────────────────────────────────────────────────────
        experience = []
        exp_sec = get_section("experience")
        if exp_sec:
            for li in exp_sec.find_all("li", class_="artdeco-list__item"):
                title     = txt(li, "div.hoverable-link-text.t-bold span[aria-hidden='true']")
                company   = txt(li, "span.t-14.t-normal:not(.t-black--light) span[aria-hidden='true']")
                date_range = txt(li, "span.pvs-entity__caption-wrapper[aria-hidden='true']")
                desc_el   = li.select_one("div[class*='inline-show-more-text'] span[aria-hidden='true']")
                desc      = desc_el.get_text(strip=True) if desc_el else ""
                is_current = bool(re.search(r"\bpresent\b", date_range, re.IGNORECASE))
                if title or company:
                    experience.append({
                        "title": title, "company": company,
                        "dateRange": date_range, "isCurrent": is_current,
                        "description": desc,
                    })

        # ── Education (truncated on main page — full list via detail page) ────
        education = []
        edu_sec = get_section("education")
        if edu_sec:
            for li in edu_sec.find_all("li", class_="artdeco-list__item"):
                institution = txt(li, "div.hoverable-link-text.t-bold span[aria-hidden='true']")
                degree      = txt(li, "span.t-14.t-normal:not(.t-black--light) span[aria-hidden='true']")
                date_range  = txt(li, "span.pvs-entity__caption-wrapper[aria-hidden='true']")
                if institution and date_range:
                    education.append({"institution": institution, "degree": degree, "dateRange": date_range})

        # ── Skills (truncated on main page — full list via detail page) ───────
        skills = []
        skills_sec = get_section("skills")
        if skills_sec:
            seen = set()
            for el in skills_sec.select(
                'a[data-field="skill_card_skill_topic"] div.hoverable-link-text.t-bold span[aria-hidden="true"]'
            ):
                name_s = el.get_text(strip=True)
                if name_s and name_s not in seen:
                    seen.add(name_s)
                    skills.append(name_s)

        # ── Detail page links ─────────────────────────────────────────────────
        detail_links = {}
        for a in soup.select("a[href*='details/']"):
            h = a.get("href", "")
            t = a.get_text(strip=True).lower()
            if "education" in t or "details/education" in h:
                detail_links["education"] = h
            if "skill" in t or "details/skills" in h:
                detail_links["skills"] = h

        return {
            "name": name, "headline": headline, "location": location,
            "experience": experience, "education": education, "skills": skills,
            "detailLinks": detail_links,
        }

    # ── Detail page fetchers ───────────────────────────────────────────────────

    async def _fetch_detail_pages(
        self, browser, detail_links: dict,
        education: list, skills: list,
    ) -> tuple:
        """Fetch /details/education and /details/skills for the complete lists."""
        edu_url = detail_links.get("education")
        skills_url = detail_links.get("skills")

        if edu_url:
            try:
                edu_page = await browser.get(edu_url)
                await edu_page.sleep(2.5)
                html = await self._get_html(edu_page)
                if html:
                    soup = BeautifulSoup(html, "html.parser")
                    anchor = soup.find("div", id="education")
                    sec = anchor.find_parent("section") if anchor else soup
                    fetched = []
                    for li in sec.find_all("li", class_="artdeco-list__item"):
                        institution = NoDriverAdapter._t(li, "div.hoverable-link-text.t-bold span[aria-hidden='true']")
                        degree      = NoDriverAdapter._t(li, "span.t-14.t-normal:not(.t-black--light) span[aria-hidden='true']")
                        date_range  = NoDriverAdapter._t(li, "span.pvs-entity__caption-wrapper[aria-hidden='true']")
                        if institution and date_range:
                            fetched.append({"institution": institution, "degree": degree, "dateRange": date_range})
                    if fetched:
                        logger.debug(f"[Tier2] Education detail: {len(fetched)} entries")
                        education = fetched
            except Exception as e:
                logger.debug(f"[Tier2] Education detail failed: {e}")

        if skills_url:
            try:
                sk_page = await browser.get(skills_url)
                await sk_page.sleep(2.5)
                html = await self._get_html(sk_page)
                if html:
                    with open("debug_linkedin_skills.html", "w", encoding="utf-8") as f:
                        f.write(html)
                    soup = BeautifulSoup(html, "html.parser")
                    seen, fetched = set(), []
                    for el in soup.select(
                        'a[data-field="skill_page_skill_topic"] '
                        'div.hoverable-link-text.t-bold span[aria-hidden="true"]'
                    ):
                        name = el.get_text(strip=True)
                        if name and name not in seen:
                            seen.add(name)
                            fetched.append(name)
                    if fetched:
                        logger.debug(f"[Tier2] Skills detail: {len(fetched)} skills")
                        skills = fetched
            except Exception as e:
                logger.debug(f"[Tier2] Skills detail failed: {e}")

        return education, skills

    @staticmethod
    def _t(root, sel: str) -> str:
        el = root.select_one(sel)
        return el.get_text(strip=True) if el else ""

    # ── Result builder ────────────────────────────────────────────────────────

    def _build_result(
        self,
        profile: dict,
        contact_name: str,
        organization: str,
        profile_url: str,
    ) -> LinkedInResult:
        name       = profile.get("name") or ""
        headline   = profile.get("headline") or ""
        location   = profile.get("location") or ""
        experience = profile.get("experience") or []
        education  = profile.get("education") or []
        skills     = profile.get("skills") or []

        if not name and not experience:
            return LinkedInResult(
                success=False, error="Empty profile — may be private or not found",
                profile_url=profile_url,
            )

        org_lower = organization.lower().strip()

        current_entries = [e for e in experience if e.get("isCurrent")]

        # Find the specific current entry whose company (or title) matches the org.
        # A person can have multiple concurrent "Present" roles (e.g. full-time + board
        # position), so we must not blindly use current_entries[0].
        def _entry_matches(e: dict) -> bool:
            return (
                org_lower in (e.get("company") or "").lower() or
                org_lower in (e.get("title") or "").lower()
            )

        matched_entry = next((e for e in current_entries if _entry_matches(e)), None) if org_lower else None
        exp_match = matched_entry is not None
        headline_match = bool(org_lower) and org_lower in headline.lower()
        still_at = exp_match or headline_match

        current_title: Optional[str] = None
        if exp_match and matched_entry:
            # Use the title from the entry that actually matched the org.
            current_title = matched_entry.get("title") or None
        elif current_entries and not org_lower:
            # No org supplied — just return the most recent current role.
            current_title = current_entries[0].get("title") or None
        elif headline_match:
            m = re.match(r"^(.+?)\s+at\s+.+$", headline, re.IGNORECASE)
            current_title = m.group(1).strip() if m else headline

        logger.info(
            f"[Tier2] {contact_name} @ {organization!r}: "
            f"still_at={still_at} title={current_title!r} "
            f"(exp={exp_match} headline={headline_match} "
            f"current_roles={len(current_entries)})"
        )

        return LinkedInResult(
            success=True,
            still_at_organization=still_at,
            current_title=current_title,
            current_organization=organization if still_at else None,
            profile_url=profile_url,
            name=name, headline=headline, location=location,
            experience=experience, education=education, skills=skills,
        )

    # ── Cookie helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _build_cookies(uc) -> list:
        """
        Load cookies from JSON file (preferred) or LINKEDIN_COOKIES_STRING env var.
        JSON file: linkedincookie.json in project root, or LINKEDIN_COOKIES_FILE env var.
        """
        json_path = os.environ.get(
            "LINKEDIN_COOKIES_FILE",
            os.path.join(os.path.dirname(__file__), "..", "..", "linkedincookie.json"),
        )
        json_path = os.path.abspath(json_path)
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as fh:
                    raw_cookies = json.load(fh)
                cookies = []
                for c in raw_cookies:
                    name = (c.get("name") or "").strip()
                    value = (c.get("value") or "").strip()
                    if not name:
                        continue
                    cookies.append(
                        uc.cdp.network.CookieParam(
                            name=name, value=value,
                            domain=c.get("domain", ".linkedin.com"),
                            path=c.get("path", "/"),
                            secure=c.get("secure", True),
                            http_only=c.get("httpOnly", False),
                        )
                    )
                logger.debug(f"[Tier2] Loaded {len(cookies)} cookies from {json_path}")
                return cookies
            except Exception as exc:
                logger.warning(f"[Tier2] Failed to load cookie JSON: {exc}")

        cookies_string = os.environ.get("LINKEDIN_COOKIES_STRING", "").strip()
        if not cookies_string:
            return []
        cookies = []
        for part in cookies_string.split(";"):
            part = part.strip()
            if "=" not in part:
                continue
            name, _, value = part.partition("=")
            name = name.strip()
            value = value.strip(' "')
            if not name:
                continue
            cookies.append(
                uc.cdp.network.CookieParam(
                    name=name, value=value,
                    domain=".linkedin.com", path="/", secure=True,
                )
            )
        return cookies
