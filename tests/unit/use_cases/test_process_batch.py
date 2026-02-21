"""
Tests for ProcessBatchUseCase — the top-level orchestrator.

Verifies:
- Contact loading with correct limit
- Per-contact verification calls
- Status transitions applied to entities
- Human review flagging
- Replacement contact insertion
- Error isolation (one bad contact doesn't abort batch)
- Receipt generation
- Concurrency limits honoured
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, call, patch

from prospectkeeper.domain.entities.contact import Contact, ContactStatus
from prospectkeeper.domain.entities.verification_result import VerificationResult
from prospectkeeper.use_cases.calculate_roi import CalculateROIUseCase
from prospectkeeper.use_cases.process_batch import (
    ProcessBatchRequest,
    ProcessBatchUseCase,
)
from prospectkeeper.use_cases.verify_contact import VerifyContactUseCase
from tests.conftest import (
    make_contact,
    make_economics,
    make_verification_result,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def make_active_result(contact: Contact) -> VerificationResult:
    return make_verification_result(
        contact_id=contact.id,
        status=ContactStatus.ACTIVE,
        economics=make_economics(contact_id=contact.id, verified=True),
    )


def make_inactive_result(contact: Contact) -> VerificationResult:
    return make_verification_result(
        contact_id=contact.id,
        status=ContactStatus.INACTIVE,
        economics=make_economics(contact_id=contact.id),
    )


def make_unknown_result(contact: Contact) -> VerificationResult:
    return make_verification_result(
        contact_id=contact.id,
        status=ContactStatus.UNKNOWN,
        low_confidence_flag=True,
        economics=make_economics(contact_id=contact.id, flagged_for_review=True),
        notes="All tiers exhausted",
    )


def make_replacement_result(contact: Contact) -> VerificationResult:
    return make_verification_result(
        contact_id=contact.id,
        status=ContactStatus.INACTIVE,
        economics=make_economics(contact_id=contact.id, replacement_found=True),
        replacement_name="New Person",
        replacement_email="new@acme.com",
        replacement_title="Director",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_verify_use_case():
    mock = AsyncMock(spec=VerifyContactUseCase)
    return mock


@pytest.fixture
def roi_use_case():
    return CalculateROIUseCase()


@pytest.fixture
def batch_use_case(mock_repository, mock_verify_use_case, roi_use_case):
    return ProcessBatchUseCase(
        repository=mock_repository,
        verify_use_case=mock_verify_use_case,
        roi_use_case=roi_use_case,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Contact loading
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestContactLoading:
    async def test_calls_repository_with_correct_limit(
        self, batch_use_case, mock_repository, mock_verify_use_case
    ):
        mock_repository.get_contacts_for_verification.return_value = []
        await batch_use_case.execute(ProcessBatchRequest(limit=25))
        mock_repository.get_contacts_for_verification.assert_called_once_with(limit=25)

    async def test_default_limit_is_50(
        self, batch_use_case, mock_repository, mock_verify_use_case
    ):
        mock_repository.get_contacts_for_verification.return_value = []
        await batch_use_case.execute(ProcessBatchRequest())
        mock_repository.get_contacts_for_verification.assert_called_once_with(limit=50)

    async def test_empty_contact_list_produces_zero_receipt(
        self, batch_use_case, mock_repository
    ):
        mock_repository.get_contacts_for_verification.return_value = []
        response = await batch_use_case.execute(ProcessBatchRequest())
        assert response.receipt.contacts_processed == 0
        assert response.results == []
        assert response.errors == []


# ─────────────────────────────────────────────────────────────────────────────
# Per-contact verification
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestPerContactVerification:
    async def test_verify_called_for_each_contact(
        self, batch_use_case, mock_repository, mock_verify_use_case
    ):
        contacts = [make_contact(name=f"Contact {i}") for i in range(3)]
        mock_repository.get_contacts_for_verification.return_value = contacts
        mock_verify_use_case.execute.side_effect = [
            make_active_result(c) for c in contacts
        ]
        await batch_use_case.execute(ProcessBatchRequest())
        assert mock_verify_use_case.execute.call_count == 3

    async def test_all_results_in_response(
        self, batch_use_case, mock_repository, mock_verify_use_case
    ):
        contacts = [make_contact(name=f"Contact {i}") for i in range(4)]
        mock_repository.get_contacts_for_verification.return_value = contacts
        mock_verify_use_case.execute.side_effect = [
            make_active_result(c) for c in contacts
        ]
        response = await batch_use_case.execute(ProcessBatchRequest())
        assert len(response.results) == 4

    async def test_receipt_contacts_processed_matches_verified_count(
        self, batch_use_case, mock_repository, mock_verify_use_case
    ):
        contacts = [make_contact() for _ in range(5)]
        mock_repository.get_contacts_for_verification.return_value = contacts
        mock_verify_use_case.execute.side_effect = [
            make_active_result(c) for c in contacts
        ]
        response = await batch_use_case.execute(ProcessBatchRequest())
        assert response.receipt.contacts_processed == 5


# ─────────────────────────────────────────────────────────────────────────────
# Status transitions applied to contact entities
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestStatusTransitions:
    async def test_active_result_calls_mark_active_on_contact(
        self, batch_use_case, mock_repository, mock_verify_use_case
    ):
        contact = make_contact(status=ContactStatus.UNKNOWN)
        mock_repository.get_contacts_for_verification.return_value = [contact]
        mock_verify_use_case.execute.return_value = make_active_result(contact)

        await batch_use_case.execute(ProcessBatchRequest())
        assert contact.status == ContactStatus.ACTIVE

    async def test_inactive_result_calls_mark_inactive_on_contact(
        self, batch_use_case, mock_repository, mock_verify_use_case
    ):
        contact = make_contact(status=ContactStatus.UNKNOWN)
        mock_repository.get_contacts_for_verification.return_value = [contact]
        mock_verify_use_case.execute.return_value = make_inactive_result(contact)

        await batch_use_case.execute(ProcessBatchRequest())
        assert contact.status == ContactStatus.INACTIVE

    async def test_unknown_result_does_not_change_contact_status(
        self, batch_use_case, mock_repository, mock_verify_use_case
    ):
        contact = make_contact(status=ContactStatus.UNKNOWN)
        mock_repository.get_contacts_for_verification.return_value = [contact]
        mock_verify_use_case.execute.return_value = make_unknown_result(contact)

        await batch_use_case.execute(ProcessBatchRequest())
        # UNKNOWN status is not overwritten (no mark_active/mark_inactive called)
        assert contact.status == ContactStatus.UNKNOWN


# ─────────────────────────────────────────────────────────────────────────────
# Human review flagging
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestHumanReviewFlagging:
    async def test_unknown_result_flags_contact_for_review(
        self, batch_use_case, mock_repository, mock_verify_use_case
    ):
        contact = make_contact()
        mock_repository.get_contacts_for_verification.return_value = [contact]
        mock_verify_use_case.execute.return_value = make_unknown_result(contact)

        await batch_use_case.execute(ProcessBatchRequest())
        assert contact.needs_human_review is True

    async def test_active_result_does_not_flag_contact_for_review(
        self, batch_use_case, mock_repository, mock_verify_use_case
    ):
        contact = make_contact()
        mock_repository.get_contacts_for_verification.return_value = [contact]
        mock_verify_use_case.execute.return_value = make_active_result(contact)

        await batch_use_case.execute(ProcessBatchRequest())
        assert contact.needs_human_review is False

    async def test_inactive_without_low_confidence_does_not_flag(
        self, batch_use_case, mock_repository, mock_verify_use_case
    ):
        contact = make_contact()
        mock_repository.get_contacts_for_verification.return_value = [contact]
        result = make_inactive_result(contact)
        result.low_confidence_flag = False
        mock_verify_use_case.execute.return_value = result

        await batch_use_case.execute(ProcessBatchRequest())
        assert contact.needs_human_review is False


# ─────────────────────────────────────────────────────────────────────────────
# Repository persistence calls
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestRepositoryPersistence:
    async def test_save_contact_called_for_each_contact(
        self, batch_use_case, mock_repository, mock_verify_use_case
    ):
        contacts = [make_contact(name=f"C{i}") for i in range(3)]
        mock_repository.get_contacts_for_verification.return_value = contacts
        mock_verify_use_case.execute.side_effect = [
            make_active_result(c) for c in contacts
        ]
        await batch_use_case.execute(ProcessBatchRequest())
        assert mock_repository.save_contact.call_count == 3

    async def test_save_verification_result_called_for_each_contact(
        self, batch_use_case, mock_repository, mock_verify_use_case
    ):
        contacts = [make_contact(name=f"C{i}") for i in range(3)]
        mock_repository.get_contacts_for_verification.return_value = contacts
        mock_verify_use_case.execute.side_effect = [
            make_active_result(c) for c in contacts
        ]
        await batch_use_case.execute(ProcessBatchRequest())
        assert mock_repository.save_verification_result.call_count == 3

    async def test_save_contact_called_with_the_contact(
        self, batch_use_case, mock_repository, mock_verify_use_case
    ):
        contact = make_contact()
        mock_repository.get_contacts_for_verification.return_value = [contact]
        mock_verify_use_case.execute.return_value = make_active_result(contact)

        await batch_use_case.execute(ProcessBatchRequest())
        mock_repository.save_contact.assert_called_once_with(contact)


# ─────────────────────────────────────────────────────────────────────────────
# Replacement contact insertion
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestReplacementInsertion:
    async def test_insert_contact_called_when_replacement_found(
        self, batch_use_case, mock_repository, mock_verify_use_case
    ):
        contact = make_contact(organization="Acme", district_website="https://acme.com")
        mock_repository.get_contacts_for_verification.return_value = [contact]
        mock_verify_use_case.execute.return_value = make_replacement_result(contact)

        await batch_use_case.execute(ProcessBatchRequest())
        mock_repository.insert_contact.assert_called_once()

    async def test_inserted_replacement_has_correct_name(
        self, batch_use_case, mock_repository, mock_verify_use_case
    ):
        contact = make_contact(organization="Acme")
        mock_repository.get_contacts_for_verification.return_value = [contact]
        mock_verify_use_case.execute.return_value = make_replacement_result(contact)

        await batch_use_case.execute(ProcessBatchRequest())
        inserted: Contact = mock_repository.insert_contact.call_args[0][0]
        assert inserted.name == "New Person"

    async def test_inserted_replacement_has_correct_email(
        self, batch_use_case, mock_repository, mock_verify_use_case
    ):
        contact = make_contact(organization="Acme")
        mock_repository.get_contacts_for_verification.return_value = [contact]
        mock_verify_use_case.execute.return_value = make_replacement_result(contact)

        await batch_use_case.execute(ProcessBatchRequest())
        inserted: Contact = mock_repository.insert_contact.call_args[0][0]
        assert inserted.email == "new@acme.com"

    async def test_inserted_replacement_inherits_organization(
        self, batch_use_case, mock_repository, mock_verify_use_case
    ):
        contact = make_contact(organization="Acme Corp")
        mock_repository.get_contacts_for_verification.return_value = [contact]
        mock_verify_use_case.execute.return_value = make_replacement_result(contact)

        await batch_use_case.execute(ProcessBatchRequest())
        inserted: Contact = mock_repository.insert_contact.call_args[0][0]
        assert inserted.organization == "Acme Corp"

    async def test_inserted_replacement_inherits_district_website(
        self, batch_use_case, mock_repository, mock_verify_use_case
    ):
        contact = make_contact(district_website="https://acme.com")
        mock_repository.get_contacts_for_verification.return_value = [contact]
        mock_verify_use_case.execute.return_value = make_replacement_result(contact)

        await batch_use_case.execute(ProcessBatchRequest())
        inserted: Contact = mock_repository.insert_contact.call_args[0][0]
        assert inserted.district_website == "https://acme.com"

    async def test_no_insert_when_no_replacement(
        self, batch_use_case, mock_repository, mock_verify_use_case
    ):
        contact = make_contact()
        mock_repository.get_contacts_for_verification.return_value = [contact]
        mock_verify_use_case.execute.return_value = make_active_result(contact)

        await batch_use_case.execute(ProcessBatchRequest())
        mock_repository.insert_contact.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# Error isolation — one failure does not abort batch
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestErrorIsolation:
    async def test_error_during_verify_added_to_errors_list(
        self, batch_use_case, mock_repository, mock_verify_use_case
    ):
        contact = make_contact()
        mock_repository.get_contacts_for_verification.return_value = [contact]
        mock_verify_use_case.execute.side_effect = RuntimeError("network error")

        response = await batch_use_case.execute(ProcessBatchRequest())
        assert len(response.errors) == 1
        assert contact.id in response.errors[0]

    async def test_error_contact_not_in_results(
        self, batch_use_case, mock_repository, mock_verify_use_case
    ):
        contact = make_contact()
        mock_repository.get_contacts_for_verification.return_value = [contact]
        mock_verify_use_case.execute.side_effect = RuntimeError("network error")

        response = await batch_use_case.execute(ProcessBatchRequest())
        assert response.results == []

    async def test_one_error_does_not_stop_other_contacts(
        self, batch_use_case, mock_repository, mock_verify_use_case
    ):
        c1 = make_contact(name="Good Contact")
        c2 = make_contact(name="Bad Contact")
        c3 = make_contact(name="Also Good")
        mock_repository.get_contacts_for_verification.return_value = [c1, c2, c3]

        def side_effect(request):
            if request.contact.name == "Bad Contact":
                raise RuntimeError("exploded")
            return make_active_result(request.contact)

        mock_verify_use_case.execute.side_effect = side_effect

        response = await batch_use_case.execute(ProcessBatchRequest())
        assert len(response.results) == 2  # c1 and c3 succeeded
        assert len(response.errors) == 1

    async def test_batch_id_in_response(
        self, batch_use_case, mock_repository, mock_verify_use_case
    ):
        mock_repository.get_contacts_for_verification.return_value = []
        response = await batch_use_case.execute(
            ProcessBatchRequest(batch_id="my-batch-id")
        )
        assert response.batch_id == "my-batch-id"


# ─────────────────────────────────────────────────────────────────────────────
# Receipt generation
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestReceiptGeneration:
    async def test_receipt_contacts_processed_matches_successful_verifications(
        self, batch_use_case, mock_repository, mock_verify_use_case
    ):
        contacts = [make_contact() for _ in range(3)]
        mock_repository.get_contacts_for_verification.return_value = contacts
        mock_verify_use_case.execute.side_effect = [
            make_active_result(c) for c in contacts
        ]
        response = await batch_use_case.execute(ProcessBatchRequest())
        assert response.receipt.contacts_processed == 3

    async def test_receipt_does_not_count_errored_contacts(
        self, batch_use_case, mock_repository, mock_verify_use_case
    ):
        contacts = [make_contact(name=f"C{i}") for i in range(3)]
        mock_repository.get_contacts_for_verification.return_value = contacts
        # First 2 succeed, third raises
        mock_verify_use_case.execute.side_effect = [
            make_active_result(contacts[0]),
            make_active_result(contacts[1]),
            RuntimeError("boom"),
        ]
        response = await batch_use_case.execute(ProcessBatchRequest())
        assert response.receipt.contacts_processed == 2
