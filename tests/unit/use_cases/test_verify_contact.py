"""
Tests for VerifyContactUseCase — the Economic Brain.

Every routing path is exhaustively tested:
  - Email validation short-circuits on definitive invalids (both tiers)
  - Free tier: valid email → confirmation email sent → PENDING_CONFIRMATION
  - Free tier: confirmation email fails → flagged for human review
  - Paid tier: website scraper confirms active
  - Paid tier: website fails → Claude AI research
  - Paid tier: all steps exhausted → flag for human review

Economics tracking is verified independently for each path.
"""

import pytest
from unittest.mock import AsyncMock, call

from prospectkeeper.domain.entities.contact import ContactStatus
from prospectkeeper.domain.interfaces.i_email_verification_gateway import EmailStatus
from prospectkeeper.use_cases.verify_contact import VerifyContactRequest, VerifyContactUseCase
from tests.conftest import (
    make_ai_result,
    make_contact,
    make_email_result,
    make_scraper_result,
    make_send_email_result,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixture: VerifyContactUseCase wired with mock gateways
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def use_case(mock_scraper, mock_ai, mock_email_verifier, mock_email_sender):
    return VerifyContactUseCase(
        scraper=mock_scraper,
        ai=mock_ai,
        email_verifier=mock_email_verifier,
        email_sender=mock_email_sender,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Email validation — short-circuit on definitive invalids (both tiers)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestEmailValidation:
    @pytest.mark.parametrize("bad_status", [
        EmailStatus.INVALID,
        EmailStatus.SPAMTRAP,
        EmailStatus.ABUSE,
        EmailStatus.DO_NOT_MAIL,
    ])
    async def test_definitively_invalid_email_returns_inactive(
        self, bad_status, use_case, mock_email_verifier
    ):
        mock_email_verifier.verify_email.return_value = make_email_result(
            status=bad_status, is_valid=False
        )
        contact = make_contact()
        result = await use_case.execute(VerifyContactRequest(contact=contact))
        assert result.status == ContactStatus.INACTIVE

    @pytest.mark.parametrize("bad_status", [
        EmailStatus.INVALID,
        EmailStatus.SPAMTRAP,
        EmailStatus.ABUSE,
        EmailStatus.DO_NOT_MAIL,
    ])
    async def test_definitively_invalid_email_does_not_call_scraper(
        self, bad_status, use_case, mock_email_verifier, mock_scraper
    ):
        mock_email_verifier.verify_email.return_value = make_email_result(
            status=bad_status, is_valid=False
        )
        await use_case.execute(VerifyContactRequest(contact=make_contact()))
        mock_scraper.find_contact_on_district_site.assert_not_called()

    @pytest.mark.parametrize("bad_status", [
        EmailStatus.INVALID,
        EmailStatus.SPAMTRAP,
        EmailStatus.ABUSE,
        EmailStatus.DO_NOT_MAIL,
    ])
    async def test_definitively_invalid_email_does_not_call_ai(
        self, bad_status, use_case, mock_email_verifier, mock_ai
    ):
        mock_email_verifier.verify_email.return_value = make_email_result(
            status=bad_status, is_valid=False
        )
        await use_case.execute(VerifyContactRequest(contact=make_contact()))
        mock_ai.research_contact.assert_not_called()

    async def test_invalid_email_marks_economics_verified(
        self, use_case, mock_email_verifier
    ):
        mock_email_verifier.verify_email.return_value = make_email_result(
            status=EmailStatus.INVALID, is_valid=False
        )
        result = await use_case.execute(VerifyContactRequest(contact=make_contact()))
        assert result.economics.verified is True

    async def test_invalid_email_accumulates_zerobounce_cost(
        self, use_case, mock_email_verifier
    ):
        mock_email_verifier.verify_email.return_value = make_email_result(
            status=EmailStatus.INVALID, is_valid=False, cost_usd=0.004
        )
        result = await use_case.execute(VerifyContactRequest(contact=make_contact()))
        assert result.economics.zerobounce_cost_usd == pytest.approx(0.004)

    async def test_invalid_email_highest_tier_is_1(
        self, use_case, mock_email_verifier
    ):
        mock_email_verifier.verify_email.return_value = make_email_result(
            status=EmailStatus.INVALID, is_valid=False
        )
        result = await use_case.execute(VerifyContactRequest(contact=make_contact()))
        assert result.economics.highest_tier_used == 1

    async def test_invalid_email_notes_contains_status(
        self, use_case, mock_email_verifier
    ):
        mock_email_verifier.verify_email.return_value = make_email_result(
            status=EmailStatus.SPAMTRAP, is_valid=False, sub_status="spam_trap_list"
        )
        result = await use_case.execute(VerifyContactRequest(contact=make_contact()))
        assert "spamtrap" in result.notes

    # Invalid email should apply regardless of tier parameter
    async def test_invalid_email_returns_inactive_even_for_paid_tier(
        self, use_case, mock_email_verifier
    ):
        mock_email_verifier.verify_email.return_value = make_email_result(
            status=EmailStatus.INVALID, is_valid=False
        )
        result = await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="paid")
        )
        assert result.status == ContactStatus.INACTIVE


# ─────────────────────────────────────────────────────────────────────────────
# Free Tier: Valid email → send confirmation email
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestFreeTierConfirmation:
    async def test_valid_email_sends_confirmation_and_returns_pending(
        self, use_case, mock_email_sender
    ):
        result = await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="free")
        )
        assert result.status == ContactStatus.PENDING_CONFIRMATION
        mock_email_sender.send_confirmation.assert_called_once()

    async def test_confirmation_called_with_correct_args(
        self, use_case, mock_email_sender
    ):
        contact = make_contact(name="Alice", email="alice@org.com")
        await use_case.execute(VerifyContactRequest(contact=contact, tier="free"))
        mock_email_sender.send_confirmation.assert_called_once_with(
            email="alice@org.com", name="Alice"
        )

    async def test_confirmation_notes_contain_email(
        self, use_case, mock_email_sender
    ):
        contact = make_contact(email="test@example.com")
        result = await use_case.execute(
            VerifyContactRequest(contact=contact, tier="free")
        )
        assert "test@example.com" in result.notes

    async def test_free_tier_does_not_call_scraper(
        self, use_case, mock_scraper
    ):
        await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="free")
        )
        mock_scraper.find_contact_on_district_site.assert_not_called()

    async def test_free_tier_does_not_call_ai(
        self, use_case, mock_ai
    ):
        await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="free")
        )
        mock_ai.research_contact.assert_not_called()

    async def test_ambiguous_email_still_sends_confirmation(
        self, use_case, mock_email_verifier, mock_email_sender
    ):
        mock_email_verifier.verify_email.return_value = make_email_result(
            status=EmailStatus.CATCH_ALL, is_valid=False
        )
        result = await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="free")
        )
        assert result.status == ContactStatus.PENDING_CONFIRMATION
        mock_email_sender.send_confirmation.assert_called_once()

    async def test_confirmation_failure_flags_for_review(
        self, use_case, mock_email_sender
    ):
        mock_email_sender.send_confirmation.return_value = make_send_email_result(
            success=False, error="SMTP error"
        )
        result = await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="free")
        )
        assert result.status == ContactStatus.UNKNOWN
        assert result.low_confidence_flag is True
        assert result.economics.flagged_for_review is True

    async def test_confirmation_failure_notes_contain_error(
        self, use_case, mock_email_sender
    ):
        mock_email_sender.send_confirmation.return_value = make_send_email_result(
            success=False, error="Connection refused"
        )
        result = await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="free")
        )
        assert "Connection refused" in result.notes

    async def test_default_tier_is_free(self, use_case, mock_email_sender):
        """VerifyContactRequest defaults to tier='free'."""
        result = await use_case.execute(
            VerifyContactRequest(contact=make_contact())
        )
        assert result.status == ContactStatus.PENDING_CONFIRMATION


# ─────────────────────────────────────────────────────────────────────────────
# Paid Tier: Website scraper confirms active
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestPaidTierScraperConfirmsActive:
    async def test_person_found_returns_active(
        self, use_case, mock_scraper
    ):
        mock_scraper.find_contact_on_district_site.return_value = make_scraper_result(
            success=True, person_found=True, evidence_url="https://acme.com/team"
        )
        result = await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="paid")
        )
        assert result.status == ContactStatus.ACTIVE

    async def test_person_found_does_not_call_ai(
        self, use_case, mock_scraper, mock_ai
    ):
        mock_scraper.find_contact_on_district_site.return_value = make_scraper_result(
            success=True, person_found=True
        )
        await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="paid")
        )
        mock_ai.research_contact.assert_not_called()

    async def test_person_found_marks_economics_verified(
        self, use_case, mock_scraper
    ):
        mock_scraper.find_contact_on_district_site.return_value = make_scraper_result(
            success=True, person_found=True
        )
        result = await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="paid")
        )
        assert result.economics.verified is True

    async def test_evidence_url_included_in_result(
        self, use_case, mock_scraper
    ):
        mock_scraper.find_contact_on_district_site.return_value = make_scraper_result(
            success=True, person_found=True, evidence_url="https://acme.com/team"
        )
        result = await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="paid")
        )
        assert "https://acme.com/team" in result.evidence_urls

    async def test_no_evidence_url_not_appended_to_list(
        self, use_case, mock_scraper
    ):
        mock_scraper.find_contact_on_district_site.return_value = make_scraper_result(
            success=True, person_found=True, evidence_url=None
        )
        result = await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="paid")
        )
        assert result.evidence_urls == []

    async def test_scraper_called_with_correct_args(
        self, use_case, mock_scraper
    ):
        contact = make_contact(
            name="Alice",
            organization="Org A",
            district_website="https://org-a.com",
        )
        mock_scraper.find_contact_on_district_site.return_value = make_scraper_result()
        await use_case.execute(
            VerifyContactRequest(contact=contact, tier="paid")
        )
        mock_scraper.find_contact_on_district_site.assert_called_once_with(
            contact_name="Alice",
            organization="Org A",
            district_website="https://org-a.com",
        )

    async def test_scraper_person_not_found_escalates_to_ai(
        self, use_case, mock_scraper, mock_ai
    ):
        mock_scraper.find_contact_on_district_site.return_value = make_scraper_result(
            success=True, person_found=False
        )
        mock_ai.research_contact.return_value = make_ai_result(
            success=True, contact_still_active=True
        )
        await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="paid")
        )
        mock_ai.research_contact.assert_called_once()

    async def test_scraper_failure_escalates_to_ai(
        self, use_case, mock_scraper, mock_ai
    ):
        mock_scraper.find_contact_on_district_site.return_value = make_scraper_result(
            success=False, error="Timeout"
        )
        mock_ai.research_contact.return_value = make_ai_result(
            success=True, contact_still_active=True
        )
        await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="paid")
        )
        mock_ai.research_contact.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# Paid Tier: Claude AI — all outcome branches
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestPaidTierClaude:
    @pytest.fixture(autouse=True)
    def _scraper_fails(self, mock_scraper):
        mock_scraper.find_contact_on_district_site.return_value = make_scraper_result(
            success=False
        )

    async def test_claude_confirms_active_returns_active(
        self, use_case, mock_ai
    ):
        mock_ai.research_contact.return_value = make_ai_result(
            success=True, contact_still_active=True
        )
        result = await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="paid")
        )
        assert result.status == ContactStatus.ACTIVE

    async def test_claude_confirms_active_marks_economics_verified(
        self, use_case, mock_ai
    ):
        mock_ai.research_contact.return_value = make_ai_result(
            success=True, contact_still_active=True
        )
        result = await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="paid")
        )
        assert result.economics.verified is True

    async def test_claude_confirms_inactive_without_replacement(
        self, use_case, mock_ai
    ):
        mock_ai.research_contact.return_value = make_ai_result(
            success=True,
            contact_still_active=False,
            replacement_name=None,
            replacement_email=None,
        )
        result = await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="paid")
        )
        assert result.status == ContactStatus.INACTIVE
        assert result.has_replacement is False

    async def test_claude_inactive_without_replacement_economics_not_set(
        self, use_case, mock_ai
    ):
        mock_ai.research_contact.return_value = make_ai_result(
            success=True, contact_still_active=False, replacement_name=None
        )
        result = await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="paid")
        )
        assert result.economics.replacement_found is False

    async def test_claude_confirms_inactive_with_replacement(
        self, use_case, mock_ai
    ):
        mock_ai.research_contact.return_value = make_ai_result(
            success=True,
            contact_still_active=False,
            replacement_name="Bob New",
            replacement_email="bob.new@acme.com",
            replacement_title="Director",
        )
        result = await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="paid")
        )
        assert result.status == ContactStatus.INACTIVE
        assert result.has_replacement is True
        assert result.replacement_name == "Bob New"
        assert result.replacement_email == "bob.new@acme.com"
        assert result.replacement_title == "Director"

    async def test_claude_with_replacement_sets_economics_flag(
        self, use_case, mock_ai
    ):
        mock_ai.research_contact.return_value = make_ai_result(
            success=True,
            contact_still_active=False,
            replacement_name="Bob New",
        )
        result = await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="paid")
        )
        assert result.economics.replacement_found is True

    async def test_claude_evidence_urls_included(
        self, use_case, mock_ai
    ):
        mock_ai.research_contact.return_value = make_ai_result(
            success=True,
            contact_still_active=True,
            evidence_urls=["https://source1.com", "https://source2.com"],
        )
        result = await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="paid")
        )
        assert "https://source1.com" in result.evidence_urls
        assert "https://source2.com" in result.evidence_urls

    async def test_claude_cost_accumulated_in_economics(
        self, use_case, mock_ai
    ):
        mock_ai.research_contact.return_value = make_ai_result(
            success=True, contact_still_active=True,
            tokens_input=300, tokens_output=200, cost_usd=0.034
        )
        result = await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="paid")
        )
        assert result.economics.claude_cost_usd == pytest.approx(0.034)

    async def test_claude_tokens_accumulated_in_economics(
        self, use_case, mock_ai
    ):
        mock_ai.research_contact.return_value = make_ai_result(
            success=True, contact_still_active=True,
            tokens_input=300, tokens_output=200
        )
        result = await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="paid")
        )
        assert result.economics.tokens_used == 500  # 300 + 200

    async def test_highest_tier_used_is_2(
        self, use_case, mock_ai
    ):
        mock_ai.research_contact.return_value = make_ai_result(
            success=True, contact_still_active=True
        )
        result = await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="paid")
        )
        assert result.economics.highest_tier_used == 2

    async def test_claude_called_with_correct_args(
        self, use_case, mock_ai
    ):
        contact = make_contact(
            name="Alice", organization="Org A", title="Director"
        )
        mock_ai.research_contact.return_value = make_ai_result(
            success=True, contact_still_active=True
        )
        await use_case.execute(
            VerifyContactRequest(contact=contact, tier="paid")
        )
        mock_ai.research_contact.assert_called_once_with(
            contact_name="Alice",
            organization="Org A",
            title="Director",
            context_text=None,  # No scraper context (scraper failed)
        )

    async def test_scraper_raw_text_passed_as_context_to_claude(
        self, mock_scraper, mock_ai, mock_email_verifier, mock_email_sender
    ):
        """When scraper succeeds but person not found, raw_text is passed to Claude."""
        mock_scraper.find_contact_on_district_site.return_value = make_scraper_result(
            success=True, person_found=False, raw_text="some context from page"
        )
        mock_ai.research_contact.return_value = make_ai_result(
            success=True, contact_still_active=True
        )
        use_case = VerifyContactUseCase(
            scraper=mock_scraper,
            ai=mock_ai,
            email_verifier=mock_email_verifier,
            email_sender=mock_email_sender,
        )
        await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="paid")
        )
        _, kwargs = mock_ai.research_contact.call_args
        assert kwargs.get("context_text") == "some context from page"


# ─────────────────────────────────────────────────────────────────────────────
# Paid Tier: All steps exhausted → human review
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestPaidTierAllStepsExhausted:
    @pytest.fixture(autouse=True)
    def _all_steps_fail(self, mock_scraper, mock_ai):
        mock_scraper.find_contact_on_district_site.return_value = make_scraper_result(
            success=False
        )
        # Claude returns success=True but contact_still_active=None (inconclusive)
        mock_ai.research_contact.return_value = make_ai_result(
            success=True, contact_still_active=None
        )

    async def test_returns_unknown_status(self, use_case):
        result = await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="paid")
        )
        assert result.status == ContactStatus.UNKNOWN

    async def test_sets_low_confidence_flag(self, use_case):
        result = await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="paid")
        )
        assert result.low_confidence_flag is True

    async def test_needs_human_review_is_true(self, use_case):
        result = await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="paid")
        )
        assert result.needs_human_review is True

    async def test_economics_flagged_for_review(self, use_case):
        result = await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="paid")
        )
        assert result.economics.flagged_for_review is True

    async def test_economics_not_marked_verified(self, use_case):
        result = await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="paid")
        )
        assert result.economics.verified is False

    async def test_notes_describe_exhaustion(self, use_case):
        result = await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="paid")
        )
        assert result.notes is not None
        assert "exhausted" in result.notes.lower() or "review" in result.notes.lower()

    async def test_all_steps_exhausted_when_claude_fails(
        self, mock_scraper, mock_ai, mock_email_verifier, mock_email_sender
    ):
        """claude success=False also leads to human review."""
        mock_scraper.find_contact_on_district_site.return_value = make_scraper_result(
            success=False
        )
        mock_ai.research_contact.return_value = make_ai_result(
            success=False, error="API error"
        )
        use_case = VerifyContactUseCase(
            scraper=mock_scraper,
            ai=mock_ai,
            email_verifier=mock_email_verifier,
            email_sender=mock_email_sender,
        )
        result = await use_case.execute(
            VerifyContactRequest(contact=make_contact(), tier="paid")
        )
        assert result.status == ContactStatus.UNKNOWN
        assert result.low_confidence_flag is True
