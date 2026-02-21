"""
Tests for CalculateROIUseCase.
"""

import uuid

import pytest

from prospectkeeper.use_cases.calculate_roi import (
    CalculateROIRequest,
    CalculateROIUseCase,
)
from tests.conftest import make_economics


@pytest.fixture
def use_case():
    return CalculateROIUseCase()


class TestCalculateROIUseCaseExecute:
    def test_returns_response_with_receipt(self, use_case):
        from prospectkeeper.domain.entities.agent_economics import ValueProofReceipt
        request = CalculateROIRequest(economics_list=[], batch_id="batch-1")
        response = use_case.execute(request)
        assert isinstance(response.receipt, ValueProofReceipt)

    def test_uses_provided_batch_id(self, use_case):
        request = CalculateROIRequest(economics_list=[], batch_id="my-batch-123")
        response = use_case.execute(request)
        assert response.receipt.batch_id == "my-batch-123"

    def test_generates_uuid_when_batch_id_empty(self, use_case):
        request = CalculateROIRequest(economics_list=[], batch_id="")
        response = use_case.execute(request)
        # Must be a valid UUID
        uuid.UUID(response.receipt.batch_id)

    def test_contacts_processed_matches_list_length(self, use_case):
        economics = [make_economics() for _ in range(7)]
        request = CalculateROIRequest(economics_list=economics, batch_id="b")
        response = use_case.execute(request)
        assert response.receipt.contacts_processed == 7

    def test_empty_list_produces_zero_receipt(self, use_case):
        request = CalculateROIRequest(economics_list=[], batch_id="b")
        response = use_case.execute(request)
        assert response.receipt.contacts_processed == 0
        assert response.receipt.total_api_cost_usd == 0.0

    def test_aggregates_api_costs(self, use_case):
        economics = [
            make_economics(zerobounce_cost_usd=0.004),
            make_economics(zerobounce_cost_usd=0.004, claude_cost_usd=0.012),
        ]
        request = CalculateROIRequest(economics_list=economics, batch_id="b")
        response = use_case.execute(request)
        assert response.receipt.total_api_cost_usd == pytest.approx(0.020, abs=1e-6)

    def test_counts_verified_contacts(self, use_case):
        economics = [
            make_economics(verified=True),
            make_economics(verified=True),
            make_economics(verified=False),
        ]
        request = CalculateROIRequest(economics_list=economics, batch_id="b")
        response = use_case.execute(request)
        assert response.receipt.contacts_verified_active == 2

    def test_counts_replacements(self, use_case):
        economics = [make_economics(replacement_found=True)] * 3
        request = CalculateROIRequest(economics_list=economics, batch_id="b")
        response = use_case.execute(request)
        assert response.receipt.replacements_found == 3

    def test_counts_flagged_for_review(self, use_case):
        economics = [make_economics(flagged_for_review=True)] * 2
        request = CalculateROIRequest(economics_list=economics, batch_id="b")
        response = use_case.execute(request)
        assert response.receipt.flagged_for_review == 2

    def test_simulated_invoice_calculated(self, use_case):
        economics = [
            make_economics(replacement_found=True),
            make_economics(replacement_found=False),
        ]
        request = CalculateROIRequest(economics_list=economics, batch_id="b")
        response = use_case.execute(request)
        # 2 verifications * $0.10 + 1 replacement * $2.50
        assert response.receipt.simulated_invoice_usd == pytest.approx(2.70, abs=0.01)
