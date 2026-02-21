"""
Tests for the VerificationResult entity.
"""

import pytest

from prospectkeeper.domain.entities.contact import ContactStatus
from prospectkeeper.domain.entities.verification_result import VerificationResult
from tests.conftest import make_economics, make_verification_result


class TestHasReplacement:
    def test_true_when_both_name_and_email_set(self):
        result = make_verification_result(
            status=ContactStatus.INACTIVE,
            replacement_name="Bob Jones",
            replacement_email="bob@acme.com",
        )
        assert result.has_replacement is True

    def test_false_when_replacement_name_is_none(self):
        result = make_verification_result(
            status=ContactStatus.INACTIVE,
            replacement_name=None,
            replacement_email="bob@acme.com",
        )
        assert result.has_replacement is False

    def test_false_when_replacement_email_is_none(self):
        result = make_verification_result(
            status=ContactStatus.INACTIVE,
            replacement_name="Bob Jones",
            replacement_email=None,
        )
        assert result.has_replacement is False

    def test_false_when_both_are_none(self):
        result = make_verification_result(
            status=ContactStatus.INACTIVE,
            replacement_name=None,
            replacement_email=None,
        )
        assert result.has_replacement is False

    def test_false_for_active_contact_with_no_replacement(self):
        result = make_verification_result(status=ContactStatus.ACTIVE)
        assert result.has_replacement is False


class TestNeedsHumanReview:
    def test_true_when_low_confidence_flag_set(self):
        result = make_verification_result(
            status=ContactStatus.ACTIVE,
            low_confidence_flag=True,
        )
        assert result.needs_human_review is True

    def test_true_when_status_is_unknown(self):
        result = make_verification_result(
            status=ContactStatus.UNKNOWN,
            low_confidence_flag=False,
        )
        assert result.needs_human_review is True

    def test_true_when_both_unknown_and_low_confidence(self):
        result = make_verification_result(
            status=ContactStatus.UNKNOWN,
            low_confidence_flag=True,
        )
        assert result.needs_human_review is True

    def test_false_when_active_and_high_confidence(self):
        result = make_verification_result(
            status=ContactStatus.ACTIVE,
            low_confidence_flag=False,
        )
        assert result.needs_human_review is False

    def test_false_when_inactive_and_high_confidence(self):
        result = make_verification_result(
            status=ContactStatus.INACTIVE,
            low_confidence_flag=False,
        )
        assert result.needs_human_review is False

    def test_opted_out_without_low_confidence_does_not_need_review(self):
        result = make_verification_result(
            status=ContactStatus.OPTED_OUT,
            low_confidence_flag=False,
        )
        assert result.needs_human_review is False


class TestVerificationResultFields:
    def test_evidence_urls_default_to_empty_list(self):
        econ = make_economics()
        result = VerificationResult(
            contact_id="abc",
            status=ContactStatus.ACTIVE,
            economics=econ,
        )
        assert result.evidence_urls == []

    def test_replacement_fields_default_to_none(self):
        econ = make_economics()
        result = VerificationResult(
            contact_id="abc",
            status=ContactStatus.INACTIVE,
            economics=econ,
        )
        assert result.replacement_name is None
        assert result.replacement_email is None
        assert result.replacement_title is None

    def test_notes_field_stored_correctly(self):
        result = make_verification_result(notes="Confirmed via LinkedIn")
        assert result.notes == "Confirmed via LinkedIn"

    def test_contact_id_stored_correctly(self):
        result = make_verification_result(contact_id="contact-xyz")
        assert result.contact_id == "contact-xyz"
