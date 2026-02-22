"""
VerifyContactUseCase - The Economic Brain.

Implements 2-tier routing based on product tier:

  Free Tier  — Send confirmation email to contact
               ("Are you still reachable at ___?")
  Paid Tier  — Website scraping + Claude AI deep research
               (finds missing info, replacements, updated contact details)

Escalates to Claude only when website scraping fails to produce confidence.
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
from ..domain.interfaces.i_email_sender_gateway import IEmailSenderGateway

logger = logging.getLogger(__name__)


@dataclass
class VerifyContactRequest:
    contact: Contact
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
        email_sender: IEmailSenderGateway,
    ):
        self.scraper = scraper
        self.ai = ai
        self.email_sender = email_sender

    async def execute(self, request: VerifyContactRequest) -> VerificationResult:
        contact = request.contact
        tier = request.tier
        economics = AgentEconomics(contact_id=contact.id)
        evidence_urls = []
        context_text = None

        logger.info(
            f"[Verify] ── START ── {contact.name!r} | "
            f"tier={tier!r} | org={contact.organization!r} | "
            f"email={contact.email!r} | id={contact.id}"
        )

        # ── Free Tier: Send confirmation email ───────────────────────────────
        if tier == "free":
            economics.highest_tier_used = 1
            logger.info(
                f"[Free Tier] Sending confirmation email → {contact.name!r} <{contact.email}>"
            )
            send_result = await self.email_sender.send_confirmation(
                contact=contact,
            )

            if send_result.success:
                logger.info(
                    f"[Free Tier] Email sent OK → {contact.name!r} <{contact.email}> "
                    f"| status=pending_confirmation"
                )
                return VerificationResult(
                    contact_id=contact.id,
                    status=ContactStatus.PENDING_CONFIRMATION,
                    economics=economics,
                    notes="Confirmation email sent: 'Are you still reachable at "
                    f"{contact.email}?'",
                )
            else:
                logger.warning(
                    f"[Free Tier] Email FAILED → {contact.name!r} <{contact.email}> "
                    f"| error={send_result.error!r} | flagging for review"
                )
                economics.flagged_for_review = True
                return VerificationResult(
                    contact_id=contact.id,
                    status=ContactStatus.UNKNOWN,
                    economics=economics,
                    low_confidence_flag=True,
                    notes=f"Failed to send confirmation email: {send_result.error}",
                )

        # ── Paid Tier: Website Scraping + Claude AI ──────────────────────────

        # Step 1: District/Company Website Scraping
        logger.info(
            f"[Paid Tier] Step 1 — scraping district site for {contact.name!r} | "
            f"url={contact.district_website!r}"
        )
        scrape_result = await self.scraper.find_contact_on_district_site(
            contact_name=contact.name,
            organization=contact.organization,
            district_website=contact.district_website,
        )
        logger.info(
            f"[Paid Tier] Scrape result → success={scrape_result.success} | "
            f"person_found={scrape_result.person_found} | "
            f"evidence_url={scrape_result.evidence_url!r}"
        )

        if scrape_result.success:
            if scrape_result.evidence_url:
                evidence_urls.append(scrape_result.evidence_url)
            context_text = scrape_result.raw_text

            if scrape_result.person_found:
                logger.info(
                    f"[Paid Tier] CONFIRMED ACTIVE via website → {contact.name!r} | "
                    f"evidence={scrape_result.evidence_url!r}"
                )
                economics.verified = True
                return VerificationResult(
                    contact_id=contact.id,
                    status=ContactStatus.ACTIVE,
                    economics=economics,
                    evidence_urls=evidence_urls,
                    notes="Confirmed via public website",
                )

        # Step 2: Claude AI Deep Research
        logger.info(
            f"[Paid Tier] Step 2 — escalating to Claude AI for {contact.name!r} | "
            f"scrape_failed_or_not_found=True | context_chars={len(context_text or '')}"
        )
        economics.highest_tier_used = 2

        ai_result = await self.ai.research_contact(
            contact_name=contact.name,
            organization=contact.organization,
            title=contact.title,
            context_text=context_text,
        )
        logger.info(
            f"[Paid Tier] Claude result → success={ai_result.success} | "
            f"still_active={ai_result.contact_still_active} | "
            f"replacement={ai_result.replacement_name!r} | "
            f"cost=${ai_result.cost_usd:.5f} | tokens={ai_result.total_tokens}"
        )

        economics.claude_cost_usd += ai_result.cost_usd
        economics.tokens_used += ai_result.total_tokens
        evidence_urls.extend(ai_result.evidence_urls)

        if ai_result.success and ai_result.contact_still_active is not None:
            if ai_result.contact_still_active:
                logger.info(
                    f"[Paid Tier] CONFIRMED ACTIVE via Claude → {contact.name!r}"
                )
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
                logger.info(
                    f"[Paid Tier] INACTIVE (departed) → {contact.name!r} | "
                    f"replacement_found={has_replacement} | "
                    f"replacement_name={ai_result.replacement_name!r}"
                )
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
            f"[Verify] All steps exhausted for {contact.name!r} | "
            f"ai_success={ai_result.success} | ai_active={ai_result.contact_still_active} "
            f"→ flagging for human review"
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
