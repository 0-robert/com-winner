"""
Root conftest.py — shared fixtures and helpers for the entire test suite.

Provides:
- Contact factory helper
- AgentEconomics factory helper
- Mock gateway / repository factories (for use-case tests)
- Gateway stub implementations (in-memory fakes for integration-style unit tests)
"""

import uuid
from datetime import datetime
from typing import Optional
from unittest.mock import AsyncMock

import pytest

from prospectkeeper.domain.entities.agent_economics import AgentEconomics
from prospectkeeper.domain.entities.contact import Contact, ContactStatus
from prospectkeeper.domain.entities.verification_result import VerificationResult
from prospectkeeper.domain.interfaces.i_ai_gateway import AIResearchResult
from prospectkeeper.domain.interfaces.i_email_verification_gateway import (
    EmailStatus,
    EmailVerificationResult,
)
from prospectkeeper.domain.interfaces.i_email_sender_gateway import SendEmailResult
from prospectkeeper.domain.interfaces.i_scraper_gateway import ScraperResult


# ─────────────────────────────────────────────────────────────────────────────
# Domain object factories
# ─────────────────────────────────────────────────────────────────────────────


def make_contact(
    name: str = "Jane Smith",
    email: str = "jane.smith@acme.com",
    title: str = "VP of Operations",
    organization: str = "Acme Corp",
    status: ContactStatus = ContactStatus.UNKNOWN,
    needs_human_review: bool = False,
    review_reason: Optional[str] = None,
    district_website: Optional[str] = "https://acme.com",
    linkedin_url: Optional[str] = None,
    contact_id: Optional[str] = None,
) -> Contact:
    """Create a Contact with sensible test defaults."""
    return Contact(
        id=contact_id or str(uuid.uuid4()),
        name=name,
        email=email,
        title=title,
        organization=organization,
        status=status,
        needs_human_review=needs_human_review,
        review_reason=review_reason,
        district_website=district_website,
        linkedin_url=linkedin_url,
        created_at=datetime(2025, 1, 1, 12, 0, 0),
        updated_at=datetime(2025, 1, 1, 12, 0, 0),
    )


def make_economics(
    contact_id: Optional[str] = None,
    zerobounce_cost_usd: float = 0.0,
    claude_cost_usd: float = 0.0,
    tokens_used: int = 0,
    verified: bool = False,
    replacement_found: bool = False,
    flagged_for_review: bool = False,
    highest_tier_used: int = 1,
) -> AgentEconomics:
    """Create AgentEconomics with sensible test defaults."""
    return AgentEconomics(
        contact_id=contact_id or str(uuid.uuid4()),
        zerobounce_cost_usd=zerobounce_cost_usd,
        claude_cost_usd=claude_cost_usd,
        tokens_used=tokens_used,
        verified=verified,
        replacement_found=replacement_found,
        flagged_for_review=flagged_for_review,
        highest_tier_used=highest_tier_used,
    )


def make_verification_result(
    contact_id: Optional[str] = None,
    status: ContactStatus = ContactStatus.ACTIVE,
    economics: Optional[AgentEconomics] = None,
    low_confidence_flag: bool = False,
    replacement_name: Optional[str] = None,
    replacement_email: Optional[str] = None,
    replacement_title: Optional[str] = None,
    notes: Optional[str] = None,
) -> VerificationResult:
    """Create a VerificationResult with sensible test defaults."""
    cid = contact_id or str(uuid.uuid4())
    return VerificationResult(
        contact_id=cid,
        status=status,
        economics=economics or make_economics(contact_id=cid),
        low_confidence_flag=low_confidence_flag,
        replacement_name=replacement_name,
        replacement_email=replacement_email,
        replacement_title=replacement_title,
        notes=notes,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Gateway result factories
# ─────────────────────────────────────────────────────────────────────────────


def make_email_result(
    email: str = "jane.smith@acme.com",
    status: EmailStatus = EmailStatus.VALID,
    is_valid: bool = True,
    cost_usd: float = 0.004,
    sub_status: Optional[str] = None,
    error: Optional[str] = None,
) -> EmailVerificationResult:
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
        cost_usd=cost_usd,
        sub_status=sub_status,
        error=error,
    )


def make_scraper_result(
    success: bool = True,
    person_found: bool = True,
    evidence_url: Optional[str] = "https://acme.com/team",
    raw_text: Optional[str] = "jane smith director",
    error: Optional[str] = None,
) -> ScraperResult:
    return ScraperResult(
        success=success,
        person_found=person_found,
        evidence_url=evidence_url,
        raw_text=raw_text,
        error=error,
    )


def make_send_email_result(
    success: bool = True,
    email: str = "jane.smith@acme.com",
    error: Optional[str] = None,
) -> SendEmailResult:
    return SendEmailResult(
        success=success,
        email=email,
        error=error,
    )


def make_ai_result(
    success: bool = True,
    contact_still_active: Optional[bool] = True,
    replacement_name: Optional[str] = None,
    replacement_email: Optional[str] = None,
    replacement_title: Optional[str] = None,
    tokens_input: int = 200,
    tokens_output: int = 150,
    cost_usd: float = 0.003,
    evidence_urls: Optional[list] = None,
    error: Optional[str] = None,
) -> AIResearchResult:
    return AIResearchResult(
        success=success,
        contact_still_active=contact_still_active,
        replacement_name=replacement_name,
        replacement_email=replacement_email,
        replacement_title=replacement_title,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        cost_usd=cost_usd,
        evidence_urls=evidence_urls or [],
        error=error,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Mock gateway fixtures (inject into use-case tests)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_email_verifier():
    """AsyncMock for IEmailVerificationGateway. Defaults to returning a valid email."""
    mock = AsyncMock()
    mock.verify_email.return_value = make_email_result()
    return mock


@pytest.fixture
def mock_scraper():
    """AsyncMock for IScraperGateway. Defaults to finding the contact."""
    mock = AsyncMock()
    mock.find_contact_on_district_site.return_value = make_scraper_result()
    return mock


@pytest.fixture
def mock_email_sender():
    """AsyncMock for IEmailSenderGateway. Defaults to successful send."""
    mock = AsyncMock()
    mock.send_confirmation.return_value = make_send_email_result()
    return mock


@pytest.fixture
def mock_ai():
    """AsyncMock for IAIGateway. Defaults to confirming active."""
    mock = AsyncMock()
    mock.research_contact.return_value = make_ai_result()
    return mock


@pytest.fixture
def mock_repository():
    """AsyncMock for IDataRepository."""
    mock = AsyncMock()
    mock.get_contacts_for_verification.return_value = []
    mock.get_all_contacts.return_value = []
    mock.get_contacts_needing_review.return_value = []
    mock.get_contact_by_id.return_value = None
    mock.save_contact.return_value = None
    mock.save_verification_result.return_value = None
    mock.bulk_update_contacts.return_value = None
    mock.insert_contact.return_value = None
    return mock


@pytest.fixture
def sample_contact():
    """A single ready-to-use contact."""
    return make_contact()


@pytest.fixture
def sample_contact_no_website():
    """Contact with no district_website (forces Tier 1b skip)."""
    return make_contact(district_website=None, linkedin_url=None)
