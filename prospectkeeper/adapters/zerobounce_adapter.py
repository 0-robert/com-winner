"""
ZeroBounceAdapter - Implements IEmailVerificationGateway.
Tier 1: Email validation via ZeroBounce REST API.
Cost: ~$0.004 per credit.
"""

import logging
from typing import Optional

import httpx

from ..domain.interfaces.i_email_verification_gateway import (
    IEmailVerificationGateway,
    EmailVerificationResult,
    EmailStatus,
)

logger = logging.getLogger(__name__)

ZEROBOUNCE_API_URL = "https://api.zerobounce.net/v2/validate"
COST_PER_CREDIT = 0.004


class ZeroBounceAdapter(IEmailVerificationGateway):
    """
    Email validation adapter using ZeroBounce.
    ZeroBounce provides:
    - Syntax validation
    - MX record checks
    - SMTP verification
    - Spam trap & abuse detection
    """

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def verify_email(self, email: str) -> EmailVerificationResult:
        if not email or not self.api_key:
            return EmailVerificationResult(
                email=email,
                status=EmailStatus.UNKNOWN,
                deliverability="Unknown",
                is_valid=False,
                cost_usd=0.0,
                error="Missing email or API key",
            )

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    ZEROBOUNCE_API_URL,
                    params={"api_key": self.api_key, "email": email},
                )
                response.raise_for_status()
                data = response.json()

            raw_status = data.get("status", "unknown").lower()
            status = self._map_status(raw_status)
            sub_status = data.get("sub_status")

            is_valid = status == EmailStatus.VALID
            deliverability = (
                "Deliverable"
                if is_valid
                else "Risky"
                if status in (EmailStatus.CATCH_ALL, EmailStatus.UNKNOWN)
                else "Undeliverable"
            )

            return EmailVerificationResult(
                email=email,
                status=status,
                deliverability=deliverability,
                is_valid=is_valid,
                cost_usd=COST_PER_CREDIT,
                sub_status=sub_status,
            )

        except httpx.TimeoutException:
            logger.warning(f"[ZeroBounce] Timeout verifying {email}")
            return EmailVerificationResult(
                email=email,
                status=EmailStatus.UNKNOWN,
                deliverability="Unknown",
                is_valid=False,
                cost_usd=0.0,
                error="Timeout",
            )
        except Exception as e:
            logger.error(f"[ZeroBounce] Error: {e}")
            return EmailVerificationResult(
                email=email,
                status=EmailStatus.UNKNOWN,
                deliverability="Unknown",
                is_valid=False,
                cost_usd=0.0,
                error=str(e),
            )

    def _map_status(self, raw: str) -> EmailStatus:
        mapping = {
            "valid": EmailStatus.VALID,
            "invalid": EmailStatus.INVALID,
            "catch-all": EmailStatus.CATCH_ALL,
            "unknown": EmailStatus.UNKNOWN,
            "spamtrap": EmailStatus.SPAMTRAP,
            "abuse": EmailStatus.ABUSE,
            "do-not-mail": EmailStatus.DO_NOT_MAIL,
        }
        return mapping.get(raw, EmailStatus.UNKNOWN)
