"""
Tests for VerifyContactUseCase — the Economic Brain.

Every tiered routing path is exhaustively tested:
  - Tier 1a: Email validation short-circuits on definitive invalids
  - Tier 1b: Website scraper confirms/denies presence
  - Tier 2:  LinkedIn confirms/denies/blocks
  - Tier 3:  Claude confirms active, inactive + replacement, inactive no replacement
  - Fallback: All tiers exhausted → flag for human review

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
    make_linkedin_result,
    make_scraper_result,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixture: VerifyContactUseCase wired with mock gateways
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def use_case(mock_scraper, mock_linkedin, mock_ai, mock_email_verifier):
    return VerifyContactUseCase(
        scraper=mock_scraper,
        linkedin=mock_linkedin,
        ai=mock_ai,
        email_verifier=mock_email_verifier,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Tier 1a: Email validation — short-circuit on definitive invalids
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestTier1aEmailValidation:
    @pytest.mark.parametrize("bad_status", [
        EmailStatus.INVALID,
        EmailStatus.SPAMTRAP,
        EmailStatus.ABUSE,
        EmailStatus.DO_NOT_MAIL,
    ])
    async def test_definitively_invalid_email_returns_inactive(
        self, bad_status, use_case, mock_email_verifier, mock_scraper
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
    async def test_definitively_invalid_email_does_not_call_linkedin_or_ai(
        self, bad_status, use_case, mock_email_verifier, mock_linkedin, mock_ai
    ):
        mock_email_verifier.verify_email.return_value = make_email_result(
            status=bad_status, is_valid=False
        )
        await use_case.execute(VerifyContactRequest(contact=make_contact()))
        mock_linkedin.verify_employment.assert_not_called()
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

    @pytest.mark.parametrize("ambiguous_status", [
        EmailStatus.CATCH_ALL,
        EmailStatus.UNKNOWN,
    ])
    async def test_ambiguous_email_does_not_short_circuit(
        self, ambiguous_status, use_case, mock_email_verifier, mock_scraper
    ):
        """CATCH_ALL and UNKNOWN must NOT short-circuit — scraper is called."""
        mock_email_verifier.verify_email.return_value = make_email_result(
            status=ambiguous_status, is_valid=False
        )
        mock_scraper.find_contact_on_district_site.return_value = make_scraper_result(
            success=True, person_found=True
        )
        result = await use_case.execute(VerifyContactRequest(contact=make_contact()))
        mock_scraper.find_contact_on_district_site.assert_called_once()
        assert result.status == ContactStatus.ACTIVE

    async def test_valid_email_does_not_short_circuit(
        self, use_case, mock_email_verifier, mock_scraper
    ):
        mock_email_verifier.verify_email.return_value = make_email_result(
            status=EmailStatus.VALID, is_valid=True
        )
        mock_scraper.find_contact_on_district_site.return_value = make_scraper_result(
            success=True, person_found=True
        )
        await use_case.execute(VerifyContactRequest(contact=make_contact()))
        mock_scraper.find_contact_on_district_site.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# Tier 1b: Website scraper — confirms active
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestTier1bScraperConfirmsActive:
    async def test_person_found_returns_active(
        self, use_case, mock_scraper
    ):
        mock_scraper.find_contact_on_district_site.return_value = make_scraper_result(
            success=True, person_found=True, evidence_url="https://acme.com/team"
        )
        result = await use_case.execute(VerifyContactRequest(contact=make_contact()))
        assert result.status == ContactStatus.ACTIVE

    async def test_person_found_does_not_call_linkedin(
        self, use_case, mock_scraper, mock_linkedin
    ):
        mock_scraper.find_contact_on_district_site.return_value = make_scraper_result(
            success=True, person_found=True
        )
        await use_case.execute(VerifyContactRequest(contact=make_contact()))
        mock_linkedin.verify_employment.assert_not_called()

    async def test_person_found_does_not_call_ai(
        self, use_case, mock_scraper, mock_ai
    ):
        mock_scraper.find_contact_on_district_site.return_value = make_scraper_result(
            success=True, person_found=True
        )
        await use_case.execute(VerifyContactRequest(contact=make_contact()))
        mock_ai.research_contact.assert_not_called()

    async def test_person_found_marks_economics_verified(
        self, use_case, mock_scraper
    ):
        mock_scraper.find_contact_on_district_site.return_value = make_scraper_result(
            success=True, person_found=True
        )
        result = await use_case.execute(VerifyContactRequest(contact=make_contact()))
        assert result.economics.verified is True

    async def test_evidence_url_included_in_result(
        self, use_case, mock_scraper
    ):
        mock_scraper.find_contact_on_district_site.return_value = make_scraper_result(
            success=True, person_found=True, evidence_url="https://acme.com/team"
        )
        result = await use_case.execute(VerifyContactRequest(contact=make_contact()))
        assert "https://acme.com/team" in result.evidence_urls

    async def test_no_evidence_url_not_appended_to_list(
        self, use_case, mock_scraper
    ):
        mock_scraper.find_contact_on_district_site.return_value = make_scraper_result(
            success=True, person_found=True, evidence_url=None
        )
        result = await use_case.execute(VerifyContactRequest(contact=make_contact()))
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
        await use_case.execute(VerifyContactRequest(contact=contact))
        mock_scraper.find_contact_on_district_site.assert_called_once_with(
            contact_name="Alice",
            organization="Org A",
            district_website="https://org-a.com",
        )

    async def test_scraper_person_not_found_escalates_to_linkedin(
        self, use_case, mock_scraper, mock_linkedin
    ):
        mock_scraper.find_contact_on_district_site.return_value = make_scraper_result(
            success=True, person_found=False
        )
        mock_linkedin.verify_employment.return_value = make_linkedin_result(
            success=True, still_at_organization=True
        )
        await use_case.execute(VerifyContactRequest(contact=make_contact()))
        mock_linkedin.verify_employment.assert_called_once()

    async def test_scraper_failure_escalates_to_linkedin(
        self, use_case, mock_scraper, mock_linkedin
    ):
        mock_scraper.find_contact_on_district_site.return_value = make_scraper_result(
            success=False, error="Timeout"
        )
        mock_linkedin.verify_employment.return_value = make_linkedin_result(
            success=True, still_at_organization=True
        )
        await use_case.execute(VerifyContactRequest(contact=make_contact()))
        mock_linkedin.verify_employment.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# Tier 2: LinkedIn — confirms active
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestTier2LinkedInConfirmsActive:
    @pytest.fixture(autouse=True)
    def _scraper_fails(self, mock_scraper):
        mock_scraper.find_contact_on_district_site.return_value = make_scraper_result(
            success=False, error="No directory found"
        )

    async def test_still_at_org_true_returns_active(
        self, use_case, mock_linkedin
    ):
        mock_linkedin.verify_employment.return_value = make_linkedin_result(
            success=True, still_at_organization=True
        )
        result = await use_case.execute(VerifyContactRequest(contact=make_contact()))
        assert result.status == ContactStatus.ACTIVE

    async def test_still_at_org_true_does_not_call_ai(
        self, use_case, mock_linkedin, mock_ai
    ):
        mock_linkedin.verify_employment.return_value = make_linkedin_result(
            success=True, still_at_organization=True
        )
        await use_case.execute(VerifyContactRequest(contact=make_contact()))
        mock_ai.research_contact.assert_not_called()

    async def test_still_at_org_true_marks_economics_verified(
        self, use_case, mock_linkedin
    ):
        mock_linkedin.verify_employment.return_value = make_linkedin_result(
            success=True, still_at_organization=True
        )
        result = await use_case.execute(VerifyContactRequest(contact=make_contact()))
        assert result.economics.verified is True

    async def test_profile_url_added_to_evidence(
        self, use_case, mock_linkedin
    ):
        mock_linkedin.verify_employment.return_value = make_linkedin_result(
            success=True, still_at_organization=True,
            profile_url="https://linkedin.com/in/alice"
        )
        result = await use_case.execute(VerifyContactRequest(contact=make_contact()))
        assert "https://linkedin.com/in/alice" in result.evidence_urls

    async def test_no_profile_url_not_appended(
        self, use_case, mock_linkedin
    ):
        mock_linkedin.verify_employment.return_value = make_linkedin_result(
            success=True, still_at_organization=True, profile_url=None
        )
        result = await use_case.execute(VerifyContactRequest(contact=make_contact()))
        assert result.evidence_urls == []

    async def test_linkedin_called_with_correct_args(
        self, use_case, mock_linkedin
    ):
        contact = make_contact(
            name="Alice",
            organization="Org A",
            linkedin_url="https://linkedin.com/in/alice",
        )
        mock_linkedin.verify_employment.return_value = make_linkedin_result(
            success=True, still_at_organization=True
        )
        await use_case.execute(VerifyContactRequest(contact=contact))
        mock_linkedin.verify_employment.assert_called_once_with(
            contact_name="Alice",
            organization="Org A",
            linkedin_url="https://linkedin.com/in/alice",
        )

    async def test_highest_tier_used_is_2(
        self, use_case, mock_linkedin
    ):
        mock_linkedin.verify_employment.return_value = make_linkedin_result(
            success=True, still_at_organization=True
        )
        result = await use_case.execute(VerifyContactRequest(contact=make_contact()))
        assert result.economics.highest_tier_used == 2


# ─────────────────────────────────────────────────────────────────────────────
# Tier 2 → Tier 3 escalation cases
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestTier2EscalationToTier3:
    @pytest.fixture(autouse=True)
    def _scraper_fails(self, mock_scraper):
        mock_scraper.find_contact_on_district_site.return_value = make_scraper_result(
            success=False
        )

    @pytest.fixture(autouse=True)
    def _ai_confirms_active(self, mock_ai):
        mock_ai.research_contact.return_value = make_ai_result(
            success=True, contact_still_active=True
        )

    async def test_still_at_org_false_escalates_to_claude(
        self, use_case, mock_linkedin, mock_ai
    ):
        mock_linkedin.verify_employment.return_value = make_linkedin_result(
            success=True, still_at_organization=False
        )
        await use_case.execute(VerifyContactRequest(contact=make_contact()))
        mock_ai.research_contact.assert_called_once()

    async def test_linkedin_blocked_escalates_to_claude(
        self, use_case, mock_linkedin, mock_ai
    ):
        mock_linkedin.verify_employment.return_value = make_linkedin_result(
            success=False, blocked=True
        )
        await use_case.execute(VerifyContactRequest(contact=make_contact()))
        mock_ai.research_contact.assert_called_once()

    async def test_linkedin_failure_escalates_to_claude(
        self, use_case, mock_linkedin, mock_ai
    ):
        mock_linkedin.verify_employment.return_value = make_linkedin_result(
            success=False, blocked=False, error="Timeout"
        )
        await use_case.execute(VerifyContactRequest(contact=make_contact()))
        mock_ai.research_contact.assert_called_once()

    async def test_linkedin_still_at_org_none_escalates_to_claude(
        self, use_case, mock_linkedin, mock_ai
    ):
        """still_at_organization=None means inconclusive — must escalate."""
        mock_linkedin.verify_employment.return_value = make_linkedin_result(
            success=True, still_at_organization=None
        )
        await use_case.execute(VerifyContactRequest(contact=make_contact()))
        mock_ai.research_contact.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# Tier 3: Claude — all outcome branches
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestTier3Claude:
    @pytest.fixture(autouse=True)
    def _lower_tiers_fail(self, mock_scraper, mock_linkedin):
        mock_scraper.find_contact_on_district_site.return_value = make_scraper_result(
            success=False
        )
        mock_linkedin.verify_employment.return_value = make_linkedin_result(
            success=False
        )

    async def test_claude_confirms_active_returns_active(
        self, use_case, mock_ai
    ):
        mock_ai.research_contact.return_value = make_ai_result(
            success=True, contact_still_active=True
        )
        result = await use_case.execute(VerifyContactRequest(contact=make_contact()))
        assert result.status == ContactStatus.ACTIVE

    async def test_claude_confirms_active_marks_economics_verified(
        self, use_case, mock_ai
    ):
        mock_ai.research_contact.return_value = make_ai_result(
            success=True, contact_still_active=True
        )
        result = await use_case.execute(VerifyContactRequest(contact=make_contact()))
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
        result = await use_case.execute(VerifyContactRequest(contact=make_contact()))
        assert result.status == ContactStatus.INACTIVE
        assert result.has_replacement is False

    async def test_claude_inactive_without_replacement_economics_not_set(
        self, use_case, mock_ai
    ):
        mock_ai.research_contact.return_value = make_ai_result(
            success=True, contact_still_active=False, replacement_name=None
        )
        result = await use_case.execute(VerifyContactRequest(contact=make_contact()))
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
        result = await use_case.execute(VerifyContactRequest(contact=make_contact()))
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
        result = await use_case.execute(VerifyContactRequest(contact=make_contact()))
        assert result.economics.replacement_found is True

    async def test_claude_evidence_urls_included(
        self, use_case, mock_ai
    ):
        mock_ai.research_contact.return_value = make_ai_result(
            success=True,
            contact_still_active=True,
            evidence_urls=["https://source1.com", "https://source2.com"],
        )
        result = await use_case.execute(VerifyContactRequest(contact=make_contact()))
        assert "https://source1.com" in result.evidence_urls
        assert "https://source2.com" in result.evidence_urls

    async def test_claude_cost_accumulated_in_economics(
        self, use_case, mock_ai
    ):
        mock_ai.research_contact.return_value = make_ai_result(
            success=True, contact_still_active=True,
            tokens_input=300, tokens_output=200, cost_usd=0.034
        )
        result = await use_case.execute(VerifyContactRequest(contact=make_contact()))
        assert result.economics.claude_cost_usd == pytest.approx(0.034)

    async def test_claude_tokens_accumulated_in_economics(
        self, use_case, mock_ai
    ):
        mock_ai.research_contact.return_value = make_ai_result(
            success=True, contact_still_active=True,
            tokens_input=300, tokens_output=200
        )
        result = await use_case.execute(VerifyContactRequest(contact=make_contact()))
        assert result.economics.tokens_used == 500  # 300 + 200

    async def test_highest_tier_used_is_3(
        self, use_case, mock_ai
    ):
        mock_ai.research_contact.return_value = make_ai_result(
            success=True, contact_still_active=True
        )
        result = await use_case.execute(VerifyContactRequest(contact=make_contact()))
        assert result.economics.highest_tier_used == 3

    async def test_claude_called_with_correct_args(
        self, use_case, mock_ai
    ):
        contact = make_contact(
            name="Alice", organization="Org A", title="Director"
        )
        mock_ai.research_contact.return_value = make_ai_result(
            success=True, contact_still_active=True
        )
        await use_case.execute(VerifyContactRequest(contact=contact))
        mock_ai.research_contact.assert_called_once_with(
            contact_name="Alice",
            organization="Org A",
            title="Director",
            context_text=None,  # No scraper context (scraper failed)
        )

    async def test_scraper_raw_text_passed_as_context_to_claude(
        self, mock_scraper, mock_linkedin, mock_ai, mock_email_verifier
    ):
        """When scraper succeeds but person not found, raw_text is passed to Claude."""
        mock_scraper.find_contact_on_district_site.return_value = make_scraper_result(
            success=True, person_found=False, raw_text="some context from page"
        )
        mock_linkedin.verify_employment.return_value = make_linkedin_result(success=False)
        mock_ai.research_contact.return_value = make_ai_result(
            success=True, contact_still_active=True
        )
        use_case = VerifyContactUseCase(
            scraper=mock_scraper,
            linkedin=mock_linkedin,
            ai=mock_ai,
            email_verifier=mock_email_verifier,
        )
        await use_case.execute(VerifyContactRequest(contact=make_contact()))
        _, kwargs = mock_ai.research_contact.call_args
        assert kwargs.get("context_text") == "some context from page"


# ─────────────────────────────────────────────────────────────────────────────
# All tiers exhausted → human review
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestAllTiersExhausted:
    @pytest.fixture(autouse=True)
    def _all_tiers_fail(self, mock_scraper, mock_linkedin, mock_ai):
        mock_scraper.find_contact_on_district_site.return_value = make_scraper_result(
            success=False
        )
        mock_linkedin.verify_employment.return_value = make_linkedin_result(
            success=False
        )
        # Claude returns success=True but contact_still_active=None (inconclusive)
        mock_ai.research_contact.return_value = make_ai_result(
            success=True, contact_still_active=None
        )

    async def test_returns_unknown_status(self, use_case):
        result = await use_case.execute(VerifyContactRequest(contact=make_contact()))
        assert result.status == ContactStatus.UNKNOWN

    async def test_sets_low_confidence_flag(self, use_case):
        result = await use_case.execute(VerifyContactRequest(contact=make_contact()))
        assert result.low_confidence_flag is True

    async def test_needs_human_review_is_true(self, use_case):
        result = await use_case.execute(VerifyContactRequest(contact=make_contact()))
        assert result.needs_human_review is True

    async def test_economics_flagged_for_review(self, use_case):
        result = await use_case.execute(VerifyContactRequest(contact=make_contact()))
        assert result.economics.flagged_for_review is True

    async def test_economics_not_marked_verified(self, use_case):
        result = await use_case.execute(VerifyContactRequest(contact=make_contact()))
        assert result.economics.verified is False

    async def test_notes_describe_exhaustion(self, use_case):
        result = await use_case.execute(VerifyContactRequest(contact=make_contact()))
        assert result.notes is not None
        assert "exhausted" in result.notes.lower() or "review" in result.notes.lower()

    async def test_all_tiers_exhausted_when_claude_fails(
        self, mock_scraper, mock_linkedin, mock_ai, mock_email_verifier
    ):
        """claude success=False also leads to human review."""
        mock_scraper.find_contact_on_district_site.return_value = make_scraper_result(
            success=False
        )
        mock_linkedin.verify_employment.return_value = make_linkedin_result(
            success=False
        )
        mock_ai.research_contact.return_value = make_ai_result(
            success=False, error="API error"
        )
        use_case = VerifyContactUseCase(
            scraper=mock_scraper, linkedin=mock_linkedin,
            ai=mock_ai, email_verifier=mock_email_verifier,
        )
        result = await use_case.execute(VerifyContactRequest(contact=make_contact()))
        assert result.status == ContactStatus.UNKNOWN
        assert result.low_confidence_flag is True
