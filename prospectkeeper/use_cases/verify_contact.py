"""
VerifyContactUseCase - The Economic Brain.

Implements 2-tier routing based on product tier:

  Free Tier  — Email validation (ZeroBounce) + send confirmation email
               ("Are you still reachable at ___?")
  Paid Tier  — Email validation + website scraping + Claude AI deep research
               (finds missing info, replacements, updated contact details)

Escalates to Claude only when cheaper methods fail to produce confidence.
Flags for human review if all tiers are exhausted without confidence.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from ..domain.entities.contact import Contact, ContactStatus
from ..domain.entities.agent_economics import AgentEconomics
from ..domain.entities.verification_result import VerificationResult
from ..domain.interfaces.i_scraper_gateway import IScraperGateway
from ..domain.interfaces.i_ai_gateway import IAIGateway
from ..domain.interfaces.i_email_verification_gateway import (
    IEmailVerificationGateway,
    EmailStatus,
)
from ..domain.interfaces.i_email_sender_gateway import IEmailSenderGateway

logger = logging.getLogger(__name__)


@dataclass
class VerifyContactRequest:
    contact: Contact
    tier: str = "free"
    tier: str = "free"  # "free" or "paid"


class VerifyContactUseCase:
    """
    Orchestrates the 2-tier verification logic.
    Dependencies injected via constructor (Hexagonal Architecture).
    """

    def __init__(
        self,
        scraper: IScraperGateway,
        ai: IAIGateway,
        email_verifier: IEmailVerificationGateway,
        email_sender: IEmailSenderGateway,
    ):
        self.scraper = scraper
        self.ai = ai
        self.email_verifier = email_verifier
        self.email_sender = email_sender

    async def execute(self, request: VerifyContactRequest) -> VerificationResult:
        contact = request.contact
        tier = request.tier
        economics = AgentEconomics(contact_id=contact.id)
        evidence_urls = []
        context_text = None

        logger.info(
            f"[Verify] Starting {tier}-tier verification for "
            f"{contact.name} @ {contact.organization}"
        )

        # ── Step 1: Email Validation (both tiers) ────────────────────────────
        email_result = await self.email_verifier.verify_email(contact.email)
        economics.zerobounce_cost_usd += email_result.cost_usd
        economics.highest_tier_used = 1

        if not email_result.is_valid and email_result.status not in (
            EmailStatus.CATCH_ALL,
            EmailStatus.UNKNOWN,
        ):
            # Definitively invalid — mark inactive without escalating
            logger.info(
                f"[Email Check] Email invalid for {contact.name}: {email_result.status}"
            )
            economics.verified = True
            return VerificationResult(
                contact_id=contact.id,
                status=ContactStatus.INACTIVE,
                economics=economics,
                notes=f"Email {email_result.status.value}: {email_result.sub_status}",
            )

        # ── Free Tier: Send confirmation email ───────────────────────────────
        if tier == "free":
            logger.info(
                f"[Free Tier] Email valid/unknown for {contact.name}. "
                f"Sending confirmation email."
            )
            send_result = await self.email_sender.send_confirmation(
                email=contact.email,
                name=contact.name,
            )

            if send_result.success:
                return VerificationResult(
                    contact_id=contact.id,
                    status=ContactStatus.PENDING_CONFIRMATION,
                    economics=economics,
                    notes="Confirmation email sent: 'Are you still reachable at "
                    f"{contact.email}?'",
                )
            else:
                economics.flagged_for_review = True
                return VerificationResult(
                    contact_id=contact.id,
                    status=ContactStatus.UNKNOWN,
                    economics=economics,
                    low_confidence_flag=True,
                    notes=f"Failed to send confirmation email: {send_result.error}",
                )

        # ── Paid Tier: Website Scraping + Claude AI ──────────────────────────

        # Step 2: District/Company Website Scraping
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
                logger.info(
                    f"[Paid Tier] Confirmed active via website: {contact.name}"
                )
                economics.verified = True
                return VerificationResult(
                    contact_id=contact.id,
                    status=ContactStatus.ACTIVE,
                    economics=economics,
                    evidence_urls=evidence_urls,
                    notes="Confirmed via public website",
                )

        # Step 3: Claude AI Deep Research
        logger.info(f"[Paid Tier] Escalating to Claude for {contact.name}")
        economics.highest_tier_used = 2

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
                    notes="Confirmed active via AI research",
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
                    notes="Departed — replacement identified via AI"
                    if has_replacement
                    else "Departed — no replacement found",
                )

        # ── All steps exhausted — flag for human review ──────────────────────
        logger.warning(
            f"[All Steps] Exhausted all verification for {contact.name} "
            f"— flagging for review"
        )
        economics.flagged_for_review = True

        return VerificationResult(
            contact_id=contact.id,
            status=ContactStatus.UNKNOWN,
            economics=economics,
            low_confidence_flag=True,
            evidence_urls=evidence_urls,
            notes="All verification steps exhausted — requires human review",
        )
