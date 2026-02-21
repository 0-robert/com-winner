"""
Tests for SupabaseAdapter.
The Supabase client is mocked entirely — no real DB connections.
We test that:
  1. _row_to_contact correctly maps all fields (including optional/missing)
  2. _contact_to_row correctly serializes entities
  3. Every public method calls the Supabase client with correct chained calls
     and returns/persists correctly shaped data.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest

from prospectkeeper.adapters.supabase_adapter import (
    SupabaseAdapter,
    _contact_to_row,
    _row_to_contact,
)
from prospectkeeper.domain.entities.contact import Contact, ContactStatus
from prospectkeeper.domain.entities.verification_result import VerificationResult
from tests.conftest import make_contact, make_economics, make_verification_result


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def make_adapter() -> tuple[SupabaseAdapter, MagicMock]:
    """Return (adapter, mock_client) where mock_client mimics supabase Client."""
    with patch("prospectkeeper.adapters.supabase_adapter.create_client") as mock_create:
        mock_client = MagicMock()
        mock_create.return_value = mock_client
        adapter = SupabaseAdapter(url="https://test.supabase.co", key="test-key")
    return adapter, mock_client


def make_db_row(
    contact_id: str = "id-001",
    name: str = "Jane Smith",
    email: str = "jane@acme.com",
    title: str = "VP Operations",
    organization: str = "Acme Corp",
    status: str = "unknown",
    needs_human_review: bool = False,
    review_reason: str = None,
    district_website: str = "https://acme.com",
    linkedin_url: str = None,
    email_hash: str = None,
    created_at: str = "2025-01-01T12:00:00",
    updated_at: str = "2025-01-01T12:00:00",
) -> dict:
    return {
        "id": contact_id,
        "name": name,
        "email": email,
        "title": title,
        "organization": organization,
        "status": status,
        "needs_human_review": needs_human_review,
        "review_reason": review_reason,
        "district_website": district_website,
        "linkedin_url": linkedin_url,
        "email_hash": email_hash,
        "created_at": created_at,
        "updated_at": updated_at,
    }


def chained_execute(return_data: list) -> MagicMock:
    """Build a fluent mock where .table().select().neq()...execute() returns data."""
    execute_result = MagicMock()
    execute_result.data = return_data

    chain = MagicMock()
    chain.execute.return_value = execute_result
    chain.select.return_value = chain
    chain.neq.return_value = chain
    chain.eq.return_value = chain
    chain.limit.return_value = chain
    chain.upsert.return_value = chain
    chain.insert.return_value = chain

    return chain


# ─────────────────────────────────────────────────────────────────────────────
# _row_to_contact
# ─────────────────────────────────────────────────────────────────────────────


class TestRowToContact:
    def test_maps_id(self):
        row = make_db_row(contact_id="abc-123")
        c = _row_to_contact(row)
        assert c.id == "abc-123"

    def test_maps_name(self):
        row = make_db_row(name="Alice Johnson")
        c = _row_to_contact(row)
        assert c.name == "Alice Johnson"

    def test_maps_email(self):
        row = make_db_row(email="alice@example.com")
        c = _row_to_contact(row)
        assert c.email == "alice@example.com"

    def test_maps_title(self):
        row = make_db_row(title="Chief Product Officer")
        c = _row_to_contact(row)
        assert c.title == "Chief Product Officer"

    def test_maps_organization(self):
        row = make_db_row(organization="Global Corp")
        c = _row_to_contact(row)
        assert c.organization == "Global Corp"

    @pytest.mark.parametrize("status_str,expected_enum", [
        ("active",    ContactStatus.ACTIVE),
        ("inactive",  ContactStatus.INACTIVE),
        ("unknown",   ContactStatus.UNKNOWN),
        ("opted_out", ContactStatus.OPTED_OUT),
    ])
    def test_maps_status_enum(self, status_str, expected_enum):
        row = make_db_row(status=status_str)
        c = _row_to_contact(row)
        assert c.status == expected_enum

    def test_maps_needs_human_review_true(self):
        row = make_db_row(needs_human_review=True)
        c = _row_to_contact(row)
        assert c.needs_human_review is True

    def test_maps_needs_human_review_false(self):
        row = make_db_row(needs_human_review=False)
        c = _row_to_contact(row)
        assert c.needs_human_review is False

    def test_maps_review_reason(self):
        row = make_db_row(review_reason="Could not verify")
        c = _row_to_contact(row)
        assert c.review_reason == "Could not verify"

    def test_maps_district_website(self):
        row = make_db_row(district_website="https://example.com")
        c = _row_to_contact(row)
        assert c.district_website == "https://example.com"

    def test_maps_linkedin_url(self):
        row = make_db_row(linkedin_url="https://linkedin.com/in/alice")
        c = _row_to_contact(row)
        assert c.linkedin_url == "https://linkedin.com/in/alice"

    def test_maps_email_hash(self):
        row = make_db_row(email_hash="abc123hash")
        c = _row_to_contact(row)
        assert c.email_hash == "abc123hash"

    def test_maps_created_at_from_isoformat(self):
        row = make_db_row(created_at="2024-06-15T09:30:00")
        c = _row_to_contact(row)
        assert c.created_at == datetime(2024, 6, 15, 9, 30, 0)

    def test_maps_updated_at_from_isoformat(self):
        row = make_db_row(updated_at="2024-09-01T15:00:00")
        c = _row_to_contact(row)
        assert c.updated_at == datetime(2024, 9, 1, 15, 0, 0)

    def test_missing_email_defaults_to_empty_string(self):
        row = make_db_row()
        del row["email"]
        c = _row_to_contact(row)
        assert c.email == ""

    def test_missing_title_defaults_to_empty_string(self):
        row = make_db_row()
        del row["title"]
        c = _row_to_contact(row)
        assert c.title == ""

    def test_missing_status_defaults_to_unknown(self):
        row = make_db_row()
        del row["status"]
        c = _row_to_contact(row)
        assert c.status == ContactStatus.UNKNOWN

    def test_missing_created_at_uses_utcnow(self):
        row = make_db_row()
        row["created_at"] = None
        before = datetime.utcnow()
        c = _row_to_contact(row)
        after = datetime.utcnow()
        assert before <= c.created_at <= after


# ─────────────────────────────────────────────────────────────────────────────
# _contact_to_row
# ─────────────────────────────────────────────────────────────────────────────


class TestContactToRow:
    def test_id_serialized(self):
        c = make_contact(contact_id="xyz-999")
        row = _contact_to_row(c)
        assert row["id"] == "xyz-999"

    def test_status_serialized_as_value_string(self):
        c = make_contact(status=ContactStatus.ACTIVE)
        row = _contact_to_row(c)
        assert row["status"] == "active"

    def test_needs_human_review_serialized(self):
        c = make_contact(needs_human_review=True)
        row = _contact_to_row(c)
        assert row["needs_human_review"] is True

    def test_updated_at_is_isoformat_string(self):
        c = make_contact()
        row = _contact_to_row(c)
        # Must be parseable as ISO datetime
        datetime.fromisoformat(row["updated_at"])

    def test_all_required_keys_present(self):
        c = make_contact()
        row = _contact_to_row(c)
        required_keys = {
            "id", "name", "email", "title", "organization",
            "status", "needs_human_review", "review_reason",
            "district_website", "linkedin_url", "email_hash", "updated_at",
        }
        assert required_keys.issubset(set(row.keys()))

    def test_optional_fields_serialized_as_none(self):
        c = make_contact(district_website=None, linkedin_url=None)
        row = _contact_to_row(c)
        assert row["district_website"] is None
        assert row["linkedin_url"] is None


# ─────────────────────────────────────────────────────────────────────────────
# get_all_contacts
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestGetAllContacts:
    async def test_returns_mapped_contacts(self):
        adapter, client = make_adapter()
        row = make_db_row()
        chain = chained_execute([row])
        client.table.return_value = chain

        contacts = await adapter.get_all_contacts()
        assert len(contacts) == 1
        assert isinstance(contacts[0], Contact)
        assert contacts[0].name == "Jane Smith"

    async def test_returns_empty_list_when_no_data(self):
        adapter, client = make_adapter()
        chain = chained_execute([])
        client.table.return_value = chain

        contacts = await adapter.get_all_contacts()
        assert contacts == []

    async def test_queries_contacts_table(self):
        adapter, client = make_adapter()
        chain = chained_execute([])
        client.table.return_value = chain

        await adapter.get_all_contacts()
        client.table.assert_called_once_with("contacts")

    async def test_excludes_opted_out_contacts(self):
        adapter, client = make_adapter()
        chain = chained_execute([])
        client.table.return_value = chain

        await adapter.get_all_contacts()
        chain.neq.assert_called_once_with("status", "opted_out")


# ─────────────────────────────────────────────────────────────────────────────
# get_contacts_for_verification
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestGetContactsForVerification:
    async def test_applies_limit(self):
        adapter, client = make_adapter()
        chain = chained_execute([])
        client.table.return_value = chain

        await adapter.get_contacts_for_verification(limit=25)
        chain.limit.assert_called_once_with(25)

    async def test_excludes_opted_out(self):
        adapter, client = make_adapter()
        chain = chained_execute([])
        client.table.return_value = chain

        await adapter.get_contacts_for_verification()
        chain.neq.assert_called_once_with("status", "opted_out")

    async def test_excludes_already_flagged_contacts(self):
        adapter, client = make_adapter()
        chain = chained_execute([])
        client.table.return_value = chain

        await adapter.get_contacts_for_verification()
        chain.eq.assert_called_once_with("needs_human_review", False)

    async def test_maps_returned_rows(self):
        adapter, client = make_adapter()
        rows = [make_db_row(contact_id=f"id-{i}") for i in range(3)]
        chain = chained_execute(rows)
        client.table.return_value = chain

        contacts = await adapter.get_contacts_for_verification()
        assert len(contacts) == 3


# ─────────────────────────────────────────────────────────────────────────────
# get_contacts_needing_review
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestGetContactsNeedingReview:
    async def test_filters_on_needs_human_review_true(self):
        adapter, client = make_adapter()
        chain = chained_execute([])
        client.table.return_value = chain

        await adapter.get_contacts_needing_review()
        chain.eq.assert_called_once_with("needs_human_review", True)

    async def test_returns_mapped_contacts(self):
        adapter, client = make_adapter()
        row = make_db_row(needs_human_review=True, review_reason="Could not verify")
        chain = chained_execute([row])
        client.table.return_value = chain

        contacts = await adapter.get_contacts_needing_review()
        assert len(contacts) == 1
        assert contacts[0].needs_human_review is True


# ─────────────────────────────────────────────────────────────────────────────
# get_contact_by_id
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestGetContactById:
    async def test_returns_contact_when_found(self):
        adapter, client = make_adapter()
        chain = chained_execute([make_db_row(contact_id="id-1")])
        client.table.return_value = chain

        contact = await adapter.get_contact_by_id("id-1")
        assert contact is not None
        assert contact.id == "id-1"

    async def test_returns_none_when_not_found(self):
        adapter, client = make_adapter()
        chain = chained_execute([])
        client.table.return_value = chain

        contact = await adapter.get_contact_by_id("nonexistent")
        assert contact is None

    async def test_queries_by_id(self):
        adapter, client = make_adapter()
        chain = chained_execute([])
        client.table.return_value = chain

        await adapter.get_contact_by_id("my-id")
        chain.eq.assert_called_once_with("id", "my-id")


# ─────────────────────────────────────────────────────────────────────────────
# save_contact
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestSaveContact:
    async def test_calls_upsert_on_contacts_table(self):
        adapter, client = make_adapter()
        chain = chained_execute([])
        client.table.return_value = chain

        contact = make_contact()
        await adapter.save_contact(contact)

        client.table.assert_called_with("contacts")
        chain.upsert.assert_called_once()

    async def test_returns_the_contact(self):
        adapter, client = make_adapter()
        chain = chained_execute([])
        client.table.return_value = chain

        contact = make_contact()
        result = await adapter.save_contact(contact)
        assert result is contact

    async def test_upsert_row_contains_correct_id(self):
        adapter, client = make_adapter()
        chain = chained_execute([])
        client.table.return_value = chain

        contact = make_contact(contact_id="test-id-123")
        await adapter.save_contact(contact)

        upsert_arg = chain.upsert.call_args[0][0]
        assert upsert_arg["id"] == "test-id-123"


# ─────────────────────────────────────────────────────────────────────────────
# save_verification_result
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestSaveVerificationResult:
    async def test_inserts_into_verification_results_table(self):
        adapter, client = make_adapter()
        chain = chained_execute([])
        client.table.return_value = chain

        result = make_verification_result()
        await adapter.save_verification_result(result)

        client.table.assert_called_with("verification_results")
        chain.insert.assert_called_once()

    async def test_inserted_row_contains_contact_id(self):
        adapter, client = make_adapter()
        chain = chained_execute([])
        client.table.return_value = chain

        result = make_verification_result(contact_id="c-999")
        await adapter.save_verification_result(result)

        inserted_row = chain.insert.call_args[0][0]
        assert inserted_row["contact_id"] == "c-999"

    async def test_inserted_row_contains_api_cost(self):
        adapter, client = make_adapter()
        chain = chained_execute([])
        client.table.return_value = chain

        econ = make_economics(claude_cost_usd=0.025)
        result = make_verification_result(economics=econ)
        await adapter.save_verification_result(result)

        inserted_row = chain.insert.call_args[0][0]
        assert inserted_row["api_cost_usd"] == pytest.approx(0.025)

    async def test_inserted_row_contains_tokens_used(self):
        adapter, client = make_adapter()
        chain = chained_execute([])
        client.table.return_value = chain

        econ = make_economics(tokens_used=750)
        result = make_verification_result(economics=econ)
        await adapter.save_verification_result(result)

        inserted_row = chain.insert.call_args[0][0]
        assert inserted_row["tokens_used"] == 750

    async def test_inserted_row_contains_highest_tier_used(self):
        adapter, client = make_adapter()
        chain = chained_execute([])
        client.table.return_value = chain

        econ = make_economics(highest_tier_used=3)
        result = make_verification_result(economics=econ)
        await adapter.save_verification_result(result)

        inserted_row = chain.insert.call_args[0][0]
        assert inserted_row["highest_tier_used"] == 3

    async def test_inserted_row_has_verified_at_timestamp(self):
        adapter, client = make_adapter()
        chain = chained_execute([])
        client.table.return_value = chain

        result = make_verification_result()
        await adapter.save_verification_result(result)

        inserted_row = chain.insert.call_args[0][0]
        assert "verified_at" in inserted_row
        # Must be a valid ISO timestamp
        datetime.fromisoformat(inserted_row["verified_at"])


# ─────────────────────────────────────────────────────────────────────────────
# bulk_update_contacts
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestBulkUpdateContacts:
    async def test_calls_upsert_with_list_of_rows(self):
        adapter, client = make_adapter()
        chain = chained_execute([])
        client.table.return_value = chain

        contacts = [make_contact(name=f"C{i}") for i in range(3)]
        await adapter.bulk_update_contacts(contacts)

        chain.upsert.assert_called_once()
        upsert_arg = chain.upsert.call_args[0][0]
        assert isinstance(upsert_arg, list)
        assert len(upsert_arg) == 3


# ─────────────────────────────────────────────────────────────────────────────
# insert_contact
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestInsertContact:
    async def test_calls_insert_on_contacts_table(self):
        adapter, client = make_adapter()
        chain = chained_execute([])
        client.table.return_value = chain

        contact = make_contact()
        await adapter.insert_contact(contact)

        client.table.assert_called_with("contacts")
        chain.insert.assert_called_once()

    async def test_returns_the_contact(self):
        adapter, client = make_adapter()
        chain = chained_execute([])
        client.table.return_value = chain

        contact = make_contact()
        result = await adapter.insert_contact(contact)
        assert result is contact

    async def test_inserted_row_includes_created_at(self):
        adapter, client = make_adapter()
        chain = chained_execute([])
        client.table.return_value = chain

        contact = make_contact()
        await adapter.insert_contact(contact)

        inserted_row = chain.insert.call_args[0][0]
        assert "created_at" in inserted_row
        datetime.fromisoformat(inserted_row["created_at"])
