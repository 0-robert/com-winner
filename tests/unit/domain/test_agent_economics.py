"""
Tests for AgentEconomics and ValueProofReceipt entities.
Every property, method, edge case, and aggregation path is covered.
"""

import pytest

from prospectkeeper.domain.entities.agent_economics import (
    BILLED_RATE_PER_REPLACEMENT_USD,
    BILLED_RATE_PER_VERIFICATION_USD,
    HUMAN_HOURLY_RATE_USD,
    MINUTES_PER_CONTACT_VERIFICATION,
    MINUTES_PER_REPLACEMENT_RESEARCH,
    AgentEconomics,
    ValueProofReceipt,
)
from tests.conftest import make_economics


# ─────────────────────────────────────────────────────────────────────────────
# AgentEconomics
# ─────────────────────────────────────────────────────────────────────────────


class TestAgentEconomicsTotalApiCost:
    def test_zero_cost_by_default(self):
        econ = make_economics()
        assert econ.total_api_cost_usd == 0.0

    def test_sums_zerobounce_and_claude_costs(self):
        econ = make_economics(zerobounce_cost_usd=0.004, claude_cost_usd=0.012)
        assert econ.total_api_cost_usd == pytest.approx(0.016, abs=1e-9)

    def test_rounds_to_six_decimal_places(self):
        econ = AgentEconomics(
            contact_id="x",
            zerobounce_cost_usd=0.0000001,
            claude_cost_usd=0.0000002,
        )
        # round(0.0000003, 6) = 0.0
        assert econ.total_api_cost_usd == 0.0

    def test_fractional_costs_summed_correctly(self):
        econ = make_economics(zerobounce_cost_usd=0.001234, claude_cost_usd=0.005678)
        expected = round(0.001234 + 0.005678, 6)
        assert econ.total_api_cost_usd == expected


class TestAgentEconomicsLaborHoursSaved:
    def test_base_verification_minutes_only_when_no_replacement(self):
        econ = make_economics(replacement_found=False)
        expected = round(MINUTES_PER_CONTACT_VERIFICATION / 60.0, 4)
        assert econ.labor_hours_saved == expected

    def test_adds_replacement_minutes_when_replacement_found(self):
        econ = make_economics(replacement_found=True)
        expected = round(
            (MINUTES_PER_CONTACT_VERIFICATION + MINUTES_PER_REPLACEMENT_RESEARCH) / 60.0,
            4,
        )
        assert econ.labor_hours_saved == expected

    def test_base_value_is_5_minutes(self):
        # MINUTES_PER_CONTACT_VERIFICATION == 5
        assert MINUTES_PER_CONTACT_VERIFICATION == 5.0

    def test_replacement_adds_15_minutes(self):
        # MINUTES_PER_REPLACEMENT_RESEARCH == 15
        assert MINUTES_PER_REPLACEMENT_RESEARCH == 15.0


class TestAgentEconomicsValueGenerated:
    def test_is_labor_hours_times_hourly_rate(self):
        econ = make_economics(replacement_found=False)
        expected = round(econ.labor_hours_saved * HUMAN_HOURLY_RATE_USD, 4)
        assert econ.estimated_value_generated_usd == expected

    def test_hourly_rate_is_30(self):
        assert HUMAN_HOURLY_RATE_USD == 30.0

    def test_value_higher_when_replacement_found(self):
        econ_no_replacement = make_economics(replacement_found=False)
        econ_with_replacement = make_economics(replacement_found=True)
        assert econ_with_replacement.estimated_value_generated_usd > \
               econ_no_replacement.estimated_value_generated_usd


class TestAgentEconomicsCalculateNetROI:
    def test_returns_large_sentinel_when_zero_api_cost(self):
        econ = make_economics(zerobounce_cost_usd=0.0, claude_cost_usd=0.0)
        assert econ.calculate_net_roi() == 999_999.0

    def test_returns_large_sentinel_when_api_cost_below_threshold(self):
        # cost < 0.000001 triggers sentinel
        econ = make_economics(zerobounce_cost_usd=0.0000005)
        assert econ.calculate_net_roi() == 999_999.0

    def test_roi_formula_is_correct(self):
        econ = make_economics(zerobounce_cost_usd=0.004, claude_cost_usd=0.0,
                              replacement_found=False)
        value = econ.estimated_value_generated_usd
        cost = econ.total_api_cost_usd
        expected = round(((value - cost) / cost) * 100, 2)
        assert econ.calculate_net_roi() == expected

    def test_roi_is_positive_when_value_exceeds_cost(self):
        # $2.50 value vs $0.004 cost → very high ROI
        econ = make_economics(zerobounce_cost_usd=0.004)
        assert econ.calculate_net_roi() > 0

    def test_roi_rounds_to_two_decimal_places(self):
        econ = make_economics(zerobounce_cost_usd=0.003, claude_cost_usd=0.007)
        roi = econ.calculate_net_roi()
        assert roi == round(roi, 2)

    @pytest.mark.parametrize("zb_cost, claude_cost", [
        (0.004, 0.0),
        (0.004, 0.010),
        (0.004, 0.050),
        (0.001, 0.020),
    ])
    def test_roi_positive_for_reasonable_cost_scenarios(self, zb_cost, claude_cost):
        econ = make_economics(zerobounce_cost_usd=zb_cost, claude_cost_usd=claude_cost)
        assert econ.calculate_net_roi() > 0


# ─────────────────────────────────────────────────────────────────────────────
# ValueProofReceipt — from_economics_list
# ─────────────────────────────────────────────────────────────────────────────


class TestValueProofReceiptFromList:
    def test_empty_list_produces_zero_receipt(self):
        receipt = ValueProofReceipt.from_economics_list("batch-1", [])
        assert receipt.contacts_processed == 0
        assert receipt.contacts_verified_active == 0
        assert receipt.replacements_found == 0
        assert receipt.flagged_for_review == 0
        assert receipt.total_api_cost_usd == 0.0
        assert receipt.total_tokens_used == 0
        assert receipt.total_labor_hours_saved == 0.0
        assert receipt.total_value_generated_usd == 0.0
        assert receipt.simulated_invoice_usd == 0.0

    def test_contacts_processed_equals_length_of_list(self):
        economics = [make_economics() for _ in range(5)]
        receipt = ValueProofReceipt.from_economics_list("batch", economics)
        assert receipt.contacts_processed == 5

    def test_contacts_verified_active_counts_verified_flag(self):
        economics = [
            make_economics(verified=True),
            make_economics(verified=True),
            make_economics(verified=False),
        ]
        receipt = ValueProofReceipt.from_economics_list("batch", economics)
        assert receipt.contacts_verified_active == 2

    def test_replacements_found_counts_replacement_flag(self):
        economics = [
            make_economics(replacement_found=True),
            make_economics(replacement_found=False),
            make_economics(replacement_found=True),
        ]
        receipt = ValueProofReceipt.from_economics_list("batch", economics)
        assert receipt.replacements_found == 2

    def test_contacts_marked_inactive_equals_replacements_found(self):
        # The domain rule: replacement_found → contact_marked_inactive
        economics = [make_economics(replacement_found=True)] * 3
        receipt = ValueProofReceipt.from_economics_list("batch", economics)
        assert receipt.contacts_marked_inactive == receipt.replacements_found == 3

    def test_flagged_for_review_counts_flag(self):
        economics = [
            make_economics(flagged_for_review=True),
            make_economics(flagged_for_review=False),
            make_economics(flagged_for_review=True),
        ]
        receipt = ValueProofReceipt.from_economics_list("batch", economics)
        assert receipt.flagged_for_review == 2

    def test_total_api_cost_sums_all_contacts(self):
        economics = [
            make_economics(zerobounce_cost_usd=0.004),
            make_economics(zerobounce_cost_usd=0.004, claude_cost_usd=0.010),
        ]
        receipt = ValueProofReceipt.from_economics_list("batch", economics)
        assert receipt.total_api_cost_usd == pytest.approx(0.018, abs=1e-6)

    def test_total_tokens_used_sums_all(self):
        economics = [make_economics(tokens_used=300), make_economics(tokens_used=500)]
        receipt = ValueProofReceipt.from_economics_list("batch", economics)
        assert receipt.total_tokens_used == 800

    def test_total_labor_hours_saved_sums_all(self):
        econ1 = make_economics(replacement_found=False)
        econ2 = make_economics(replacement_found=False)
        expected = round(econ1.labor_hours_saved + econ2.labor_hours_saved, 2)
        receipt = ValueProofReceipt.from_economics_list("batch", [econ1, econ2])
        assert receipt.total_labor_hours_saved == pytest.approx(expected, abs=0.01)

    def test_batch_id_stored_correctly(self):
        receipt = ValueProofReceipt.from_economics_list("my-batch-001", [])
        assert receipt.batch_id == "my-batch-001"

    def test_simulated_invoice_verification_only(self):
        # 3 verifications, 0 replacements
        economics = [make_economics() for _ in range(3)]
        receipt = ValueProofReceipt.from_economics_list("batch", economics)
        expected = round(3 * BILLED_RATE_PER_VERIFICATION_USD, 2)
        assert receipt.simulated_invoice_usd == expected

    def test_simulated_invoice_includes_replacement_charge(self):
        economics = [
            make_economics(replacement_found=True),
            make_economics(replacement_found=True),
            make_economics(replacement_found=False),
        ]
        receipt = ValueProofReceipt.from_economics_list("batch", economics)
        expected = round(
            3 * BILLED_RATE_PER_VERIFICATION_USD + 2 * BILLED_RATE_PER_REPLACEMENT_USD,
            2,
        )
        assert receipt.simulated_invoice_usd == expected


class TestValueProofReceiptProperties:
    def test_net_roi_percentage_formula(self):
        receipt = ValueProofReceipt(
            batch_id="x",
            total_api_cost_usd=0.04,
            total_value_generated_usd=13.50,
        )
        expected = round(((13.50 - 0.04) / 0.04) * 100, 2)
        assert receipt.net_roi_percentage == expected

    def test_net_roi_returns_sentinel_when_zero_cost(self):
        receipt = ValueProofReceipt(batch_id="x", total_api_cost_usd=0.0)
        assert receipt.net_roi_percentage == 999_999.0

    def test_cost_per_contact_when_zero_contacts(self):
        receipt = ValueProofReceipt(batch_id="x", contacts_processed=0,
                                    total_api_cost_usd=0.10)
        assert receipt.cost_per_contact_usd == 0.0

    def test_cost_per_contact_calculation(self):
        receipt = ValueProofReceipt(
            batch_id="x", contacts_processed=10, total_api_cost_usd=0.40
        )
        assert receipt.cost_per_contact_usd == pytest.approx(0.04, abs=1e-6)

    def test_cost_per_replacement_when_zero_replacements(self):
        receipt = ValueProofReceipt(batch_id="x", replacements_found=0,
                                    total_api_cost_usd=0.50)
        assert receipt.cost_per_replacement_usd == 0.0

    def test_cost_per_replacement_calculation(self):
        receipt = ValueProofReceipt(
            batch_id="x", replacements_found=4, total_api_cost_usd=0.40
        )
        assert receipt.cost_per_replacement_usd == pytest.approx(0.1, abs=1e-6)


class TestFormatReceipt:
    def test_contains_contacts_processed(self):
        receipt = ValueProofReceipt(batch_id="x", contacts_processed=50)
        assert "50 Contacts Processed" in receipt.format_receipt()

    def test_contains_replacements_found(self):
        receipt = ValueProofReceipt(batch_id="x", replacements_found=12)
        assert "12 Replacements Found" in receipt.format_receipt()

    def test_contains_api_cost(self):
        receipt = ValueProofReceipt(batch_id="x", total_api_cost_usd=0.42)
        assert "$0.4200" in receipt.format_receipt()

    def test_contains_labor_hours_saved(self):
        receipt = ValueProofReceipt(batch_id="x", total_labor_hours_saved=4.5)
        assert "4.5 hours" in receipt.format_receipt()

    def test_contains_value_generated(self):
        receipt = ValueProofReceipt(batch_id="x", total_value_generated_usd=135.00)
        assert "$135.00" in receipt.format_receipt()

    def test_ends_with_roi_percentage(self):
        receipt = ValueProofReceipt(
            batch_id="x",
            total_api_cost_usd=0.42,
            total_value_generated_usd=135.0,
        )
        text = receipt.format_receipt()
        assert "%" in text
        assert text.endswith("%.")

    def test_full_format_structure(self):
        receipt = ValueProofReceipt(
            batch_id="demo",
            contacts_processed=50,
            replacements_found=12,
            total_api_cost_usd=0.42,
            total_labor_hours_saved=4.5,
            total_value_generated_usd=135.0,
        )
        text = receipt.format_receipt()
        assert text.startswith("Batch Complete:")
        assert "Contacts Processed" in text
        assert "Replacements Found" in text
        assert "Total API Cost" in text
        assert "SDR Time Saved" in text
        assert "Estimated Value Generated" in text
        assert "Net ROI" in text
