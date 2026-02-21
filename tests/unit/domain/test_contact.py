"""
Tests for the Contact entity.
Covers every method, state transition, and edge case.
"""

import hashlib
import uuid
from datetime import datetime

import pytest

from prospectkeeper.domain.entities.contact import Contact, ContactStatus
from tests.conftest import make_contact


# ─────────────────────────────────────────────────────────────────────────────
# Contact.create() factory
# ─────────────────────────────────────────────────────────────────────────────


class TestContactCreate:
    def test_create_generates_unique_id(self):
        c1 = Contact.create("Alice", "a@x.com", "Director", "Org A")
        c2 = Contact.create("Bob", "b@x.com", "Manager", "Org B")
        assert c1.id != c2.id

    def test_create_id_is_valid_uuid(self):
        c = Contact.create("Alice", "a@x.com", "Director", "Org A")
        # Must not raise:
        uuid.UUID(c.id)

    def test_create_sets_name(self):
        c = Contact.create("Alice Johnson", "a@x.com", "Director", "Org A")
        assert c.name == "Alice Johnson"

    def test_create_sets_email(self):
        c = Contact.create("Alice", "alice@example.com", "Director", "Org A")
        assert c.email == "alice@example.com"

    def test_create_sets_title(self):
        c = Contact.create("Alice", "a@x.com", "Chief Executive Officer", "Org A")
        assert c.title == "Chief Executive Officer"

    def test_create_sets_organization(self):
        c = Contact.create("Alice", "a@x.com", "Director", "ACME Corporation")
        assert c.organization == "ACME Corporation"

    def test_create_default_status_is_unknown(self):
        c = Contact.create("Alice", "a@x.com", "Director", "Org A")
        assert c.status == ContactStatus.UNKNOWN

    def test_create_default_needs_human_review_is_false(self):
        c = Contact.create("Alice", "a@x.com", "Director", "Org A")
        assert c.needs_human_review is False

    def test_create_sets_optional_district_website(self):
        c = Contact.create("Alice", "a@x.com", "Director", "Org A",
                           district_website="https://org-a.com")
        assert c.district_website == "https://org-a.com"

    def test_create_district_website_defaults_to_none(self):
        c = Contact.create("Alice", "a@x.com", "Director", "Org A")
        assert c.district_website is None

    def test_create_sets_optional_linkedin_url(self):
        c = Contact.create("Alice", "a@x.com", "Director", "Org A",
                           linkedin_url="https://linkedin.com/in/alice")
        assert c.linkedin_url == "https://linkedin.com/in/alice"

    def test_create_linkedin_url_defaults_to_none(self):
        c = Contact.create("Alice", "a@x.com", "Director", "Org A")
        assert c.linkedin_url is None

    def test_create_timestamps_are_set(self):
        before = datetime.utcnow()
        c = Contact.create("Alice", "a@x.com", "Director", "Org A")
        after = datetime.utcnow()
        assert before <= c.created_at <= after
        assert before <= c.updated_at <= after


# ─────────────────────────────────────────────────────────────────────────────
# flag_for_review()
# ─────────────────────────────────────────────────────────────────────────────


class TestFlagForReview:
    def test_sets_needs_human_review_to_true(self):
        c = make_contact()
        c.flag_for_review("Could not verify")
        assert c.needs_human_review is True

    def test_stores_review_reason(self):
        c = make_contact()
        c.flag_for_review("All tiers exhausted")
        assert c.review_reason == "All tiers exhausted"

    def test_updates_updated_at(self):
        c = make_contact()
        old_ts = c.updated_at
        c.flag_for_review("reason")
        assert c.updated_at >= old_ts

    def test_can_flag_already_flagged_contact_with_new_reason(self):
        c = make_contact()
        c.flag_for_review("first reason")
        c.flag_for_review("second reason")
        assert c.review_reason == "second reason"


# ─────────────────────────────────────────────────────────────────────────────
# clear_review_flag()
# ─────────────────────────────────────────────────────────────────────────────


class TestClearReviewFlag:
    def test_sets_needs_human_review_to_false(self):
        c = make_contact(needs_human_review=True, review_reason="some reason")
        c.clear_review_flag()
        assert c.needs_human_review is False

    def test_clears_review_reason_to_none(self):
        c = make_contact(needs_human_review=True, review_reason="some reason")
        c.clear_review_flag()
        assert c.review_reason is None

    def test_updates_updated_at(self):
        c = make_contact(needs_human_review=True, review_reason="reason")
        old_ts = c.updated_at
        c.clear_review_flag()
        assert c.updated_at >= old_ts

    def test_clears_flag_that_was_not_set(self):
        # Should be idempotent — does not raise
        c = make_contact(needs_human_review=False)
        c.clear_review_flag()
        assert c.needs_human_review is False
        assert c.review_reason is None


# ─────────────────────────────────────────────────────────────────────────────
# update_email()
# ─────────────────────────────────────────────────────────────────────────────


class TestUpdateEmail:
    def test_replaces_email_address(self):
        c = make_contact(email="old@acme.com")
        c.update_email("new@acme.com")
        assert c.email == "new@acme.com"

    def test_updates_updated_at(self):
        c = make_contact()
        old_ts = c.updated_at
        c.update_email("new@acme.com")
        assert c.updated_at >= old_ts

    def test_allows_empty_string_email(self):
        c = make_contact(email="jane@acme.com")
        c.update_email("")
        assert c.email == ""


# ─────────────────────────────────────────────────────────────────────────────
# mark_active() / mark_inactive()
# ─────────────────────────────────────────────────────────────────────────────


class TestMarkActiveInactive:
    def test_mark_active_sets_status(self):
        c = make_contact(status=ContactStatus.UNKNOWN)
        c.mark_active()
        assert c.status == ContactStatus.ACTIVE

    def test_mark_active_updates_updated_at(self):
        c = make_contact()
        old_ts = c.updated_at
        c.mark_active()
        assert c.updated_at >= old_ts

    def test_mark_inactive_sets_status(self):
        c = make_contact(status=ContactStatus.UNKNOWN)
        c.mark_inactive()
        assert c.status == ContactStatus.INACTIVE

    def test_mark_inactive_updates_updated_at(self):
        c = make_contact()
        old_ts = c.updated_at
        c.mark_inactive()
        assert c.updated_at >= old_ts

    def test_can_toggle_between_active_and_inactive(self):
        c = make_contact(status=ContactStatus.ACTIVE)
        c.mark_inactive()
        assert c.status == ContactStatus.INACTIVE
        c.mark_active()
        assert c.status == ContactStatus.ACTIVE


# ─────────────────────────────────────────────────────────────────────────────
# opt_out() — GDPR anonymization
# ─────────────────────────────────────────────────────────────────────────────


class TestOptOut:
    def test_sets_status_to_opted_out(self):
        c = make_contact()
        c.opt_out()
        assert c.status == ContactStatus.OPTED_OUT

    def test_anonymizes_name(self):
        c = make_contact(name="Jane Smith")
        c.opt_out()
        assert c.name == "[OPTED OUT]"

    def test_clears_email(self):
        c = make_contact(email="jane@acme.com")
        c.opt_out()
        assert c.email == ""

    def test_clears_title(self):
        c = make_contact(title="VP of Operations")
        c.opt_out()
        assert c.title == ""

    def test_clears_organization(self):
        c = make_contact(organization="Acme Corp")
        c.opt_out()
        assert c.organization == ""

    def test_clears_district_website(self):
        c = make_contact(district_website="https://acme.com")
        c.opt_out()
        assert c.district_website is None

    def test_clears_linkedin_url(self):
        c = make_contact(linkedin_url="https://linkedin.com/in/jane")
        c.opt_out()
        assert c.linkedin_url is None

    def test_clears_needs_human_review(self):
        c = make_contact(needs_human_review=True, review_reason="pending")
        c.opt_out()
        assert c.needs_human_review is False

    def test_retains_sha256_email_hash(self):
        email = "jane@acme.com"
        expected_hash = hashlib.sha256(email.lower().encode()).hexdigest()
        c = make_contact(email=email)
        c.opt_out()
        assert c.email_hash == expected_hash

    def test_email_hash_uses_lowercased_email(self):
        email_lower = "jane@acme.com"
        email_mixed = "Jane@ACME.com"
        expected_hash = hashlib.sha256(email_lower.encode()).hexdigest()
        c = make_contact(email=email_mixed)
        c.opt_out()
        assert c.email_hash == expected_hash

    def test_updates_updated_at(self):
        c = make_contact()
        old_ts = c.updated_at
        c.opt_out()
        assert c.updated_at >= old_ts


# ─────────────────────────────────────────────────────────────────────────────
# is_opted_out()
# ─────────────────────────────────────────────────────────────────────────────


class TestIsOptedOut:
    @pytest.mark.parametrize("status, expected", [
        (ContactStatus.UNKNOWN,    False),
        (ContactStatus.ACTIVE,     False),
        (ContactStatus.INACTIVE,   False),
        (ContactStatus.OPTED_OUT,  True),
    ])
    def test_is_opted_out_for_each_status(self, status, expected):
        c = make_contact(status=status)
        assert c.is_opted_out() == expected

    def test_is_opted_out_after_calling_opt_out(self):
        c = make_contact()
        c.opt_out()
        assert c.is_opted_out() is True


# ─────────────────────────────────────────────────────────────────────────────
# ContactStatus enum
# ─────────────────────────────────────────────────────────────────────────────


class TestContactStatus:
    def test_status_values_are_lowercase_strings(self):
        assert ContactStatus.ACTIVE.value == "active"
        assert ContactStatus.INACTIVE.value == "inactive"
        assert ContactStatus.UNKNOWN.value == "unknown"
        assert ContactStatus.OPTED_OUT.value == "opted_out"

    def test_status_is_str_enum(self):
        assert isinstance(ContactStatus.ACTIVE, str)

    def test_status_constructed_from_string(self):
        assert ContactStatus("active") == ContactStatus.ACTIVE
        assert ContactStatus("inactive") == ContactStatus.INACTIVE
        assert ContactStatus("unknown") == ContactStatus.UNKNOWN
        assert ContactStatus("opted_out") == ContactStatus.OPTED_OUT
