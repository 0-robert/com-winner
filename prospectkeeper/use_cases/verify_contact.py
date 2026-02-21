"""
VerifyContactUseCase - The Economic Brain.

Implements cost-aware tiered routing:
  Tier 1 (free)    — Public website scraping + email validation
  Tier 2 (free)    — LinkedIn verification via CamoUFox
  Tier 3 (costly)  — Deep research via Claude (Helicone-traced)

Escalates only when cheaper tiers fail.
Flags for human review if all tiers are exhausted without confidence.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from ..domain.entities.contact import Contact, ContactStatus
from ..domain.entities.agent_economics import AgentEconomics
from ..domain.entities.verification_result import VerificationResult
from ..domain.interfaces.i_scraper_gateway import IScraperGateway
from ..domain.interfaces.i_linkedin_gateway import ILinkedInGateway
from ..domain.interfaces.i_ai_gateway import IAIGateway
from ..domain.interfaces.i_email_verification_gateway import (
    IEmailVerificationGateway,
    EmailStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class VerifyContactRequest:
    contact: Contact


class VerifyContactUseCase:
    """
    Orchestrates the tiered verification logic.
    Dependencies injected via constructor (Hexagonal Architecture).
    """

    def __init__(
        self,
        scraper: IScraperGateway,
        linkedin: ILinkedInGateway,
        ai: IAIGateway,
        email_verifier: IEmailVerificationGateway,
    ):
        self.scraper = scraper
        self.linkedin = linkedin
        self.ai = ai
        self.email_verifier = email_verifier

    async def execute(self, request: VerifyContactRequest) -> VerificationResult:
        contact = request.contact
        economics = AgentEconomics(contact_id=contact.id)
        evidence_urls = []
        context_text = None

        logger.info(f"[Verify] Starting verification for {contact.name} @ {contact.organization}")

        # ── Tier 1a: Email Validation ────────────────────────────────────────
        email_result = await self.email_verifier.verify_email(contact.email)
        economics.zerobounce_cost_usd += email_result.cost_usd
        economics.highest_tier_used = 1

        if not email_result.is_valid and email_result.status not in (
            EmailStatus.CATCH_ALL,
            EmailStatus.UNKNOWN,
        ):
            # Definitively invalid — mark inactive without escalating
            logger.info(f"[Tier1] Email invalid for {contact.name}: {email_result.status}")
            economics.verified = True
            return VerificationResult(
                contact_id=contact.id,
                status=ContactStatus.INACTIVE,
                economics=economics,
                notes=f"Email {email_result.status.value}: {email_result.sub_status}",
            )

        # ── Tier 1b: District/Company Website Scraping ───────────────────────
        scrape_result = await self.scraper.find_contact_on_district_site(
            contact_name=contact.name,
            organization=contact.organization,
            district_website=contact.district_website,
        )

        if scrape_result.success:
            if scrape_result.evidence_url:
                evidence_urls.append(scrape_result.evidence_url)
            context_text = scrape_result.raw_text

            if scrape_result.person_found:
                logger.info(f"[Tier1] Confirmed active via website: {contact.name}")
                economics.verified = True
                return VerificationResult(
                    contact_id=contact.id,
                    status=ContactStatus.ACTIVE,
                    economics=economics,
                    evidence_urls=evidence_urls,
                    notes="Confirmed via public website",
                )

        # ── Tier 2: LinkedIn Verification ────────────────────────────────────
        logger.info(f"[Tier2] Escalating to LinkedIn for {contact.name}")
        economics.highest_tier_used = 2

        linkedin_result = await self.linkedin.verify_employment(
            contact_name=contact.name,
            organization=contact.organization,
            linkedin_url=contact.linkedin_url,
        )

        if linkedin_result.success and not linkedin_result.blocked:
            if linkedin_result.profile_url:
                evidence_urls.append(linkedin_result.profile_url)

            if linkedin_result.still_at_organization is True:
                logger.info(f"[Tier2] Confirmed active via LinkedIn: {contact.name}")
                economics.verified = True
                return VerificationResult(
                    contact_id=contact.id,
                    status=ContactStatus.ACTIVE,
                    economics=economics,
                    evidence_urls=evidence_urls,
                    notes="Confirmed via LinkedIn",
                )

            if linkedin_result.still_at_organization is False:
                logger.info(f"[Tier2] Confirmed departed via LinkedIn: {contact.name}")
                # Will need replacement research — escalate to Tier 3
                pass  # Fall through to Tier 3 to find replacement

        # ── Tier 3: Claude AI Deep Research ──────────────────────────────────
        logger.info(f"[Tier3] Escalating to Claude for {contact.name}")
        economics.highest_tier_used = 3

        ai_result = await self.ai.research_contact(
            contact_name=contact.name,
            organization=contact.organization,
            title=contact.title,
            context_text=context_text,
        )

        economics.claude_cost_usd += ai_result.cost_usd
        economics.tokens_used += ai_result.total_tokens
        evidence_urls.extend(ai_result.evidence_urls)

        if ai_result.success and ai_result.contact_still_active is not None:
            if ai_result.contact_still_active:
                economics.verified = True
                return VerificationResult(
                    contact_id=contact.id,
                    status=ContactStatus.ACTIVE,
                    economics=economics,
                    evidence_urls=evidence_urls,
                    notes="Confirmed active via Claude research",
                )
            else:
                # Departed — check if replacement was found
                has_replacement = bool(ai_result.replacement_name)
                economics.replacement_found = has_replacement

                return VerificationResult(
                    contact_id=contact.id,
                    status=ContactStatus.INACTIVE,
                    economics=economics,
                    replacement_name=ai_result.replacement_name,
                    replacement_email=ai_result.replacement_email,
                    replacement_title=ai_result.replacement_title,
                    evidence_urls=evidence_urls,
                    notes="Departed — replacement identified via Claude" if has_replacement
                    else "Departed — no replacement found",
                )

        # ── All tiers exhausted — flag for human review ───────────────────────
        logger.warning(f"[All Tiers] Exhausted all tiers for {contact.name} — flagging for review")
        economics.flagged_for_review = True

        return VerificationResult(
            contact_id=contact.id,
            status=ContactStatus.UNKNOWN,
            economics=economics,
            low_confidence_flag=True,
            evidence_urls=evidence_urls,
            notes="All verification tiers exhausted — requires human review",
        )
