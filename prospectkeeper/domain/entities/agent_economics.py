"""
AgentEconomics & ValueProofReceipt - Economic awareness entities.
The core of the Paid.ai "prove your value" feature.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List

# Pricing constants
HUMAN_HOURLY_RATE_USD = 30.0  # SDR hourly rate
MINUTES_PER_CONTACT_VERIFICATION = 5.0  # Manual time to verify one contact
MINUTES_PER_REPLACEMENT_RESEARCH = 15.0  # Manual time to research a replacement

# Outcome-based billing rates (simulation)
BILLED_RATE_PER_VERIFICATION_USD = 0.10
BILLED_RATE_PER_REPLACEMENT_USD = 2.50


@dataclass
class AgentEconomics:
    """
    Tracks the real-world economic cost and value of a single contact operation.
    Every action the agent takes maps to a real dollar amount.
    """

    contact_id: str

    # API costs incurred
    claude_cost_usd: float = 0.0

    # Token usage (for Helicone observability)
    tokens_used: int = 0

    # What happened
    verified: bool = False
    replacement_found: bool = False
    flagged_for_review: bool = False

    # Tier used (1=free/email, 2=paid/ai)
    highest_tier_used: int = 0

    @property
    def total_api_cost_usd(self) -> float:
        return round(self.claude_cost_usd, 6)

    @property
    def labor_hours_saved(self) -> float:
        """Calculate human-equivalent time saved for this one contact."""
        minutes = MINUTES_PER_CONTACT_VERIFICATION
        if self.replacement_found:
            minutes += MINUTES_PER_REPLACEMENT_RESEARCH
        return round(minutes / 60.0, 4)

    @property
    def estimated_value_generated_usd(self) -> float:
        """Convert saved hours to dollar value at SDR rate."""
        return round(self.labor_hours_saved * HUMAN_HOURLY_RATE_USD, 4)

    def calculate_net_roi(self) -> float:
        """
        Net ROI as a percentage.
        ((Value Generated - API Cost) / API Cost) * 100
        Returns infinity-like large number if API cost rounds to 0.
        """
        if self.total_api_cost_usd < 0.000001:
            # Free tier was sufficient — infinite ROI
            return 999_999.0
        roi = (
            (self.estimated_value_generated_usd - self.total_api_cost_usd)
            / self.total_api_cost_usd
        ) * 100
        return round(roi, 2)


@dataclass
class ValueProofReceipt:
    """
    Aggregate receipt for an entire batch run.
    Rendered on the dashboard after each ProcessBatchUseCase execution.
    """

    batch_id: str
    run_at: datetime = field(default_factory=datetime.utcnow)

    contacts_processed: int = 0
    contacts_verified_active: int = 0
    contacts_marked_inactive: int = 0
    replacements_found: int = 0
    flagged_for_review: int = 0

    total_api_cost_usd: float = 0.0
    total_tokens_used: int = 0
    total_labor_hours_saved: float = 0.0
    total_value_generated_usd: float = 0.0

    # Simulated outcome-based invoice
    simulated_invoice_usd: float = 0.0

    @property
    def net_roi_percentage(self) -> float:
        if self.total_api_cost_usd < 0.000001:
            return 999_999.0
        roi = (
            (self.total_value_generated_usd - self.total_api_cost_usd)
            / self.total_api_cost_usd
        ) * 100
        return round(roi, 2)

    @property
    def cost_per_contact_usd(self) -> float:
        if self.contacts_processed == 0:
            return 0.0
        return round(self.total_api_cost_usd / self.contacts_processed, 6)

    @property
    def cost_per_replacement_usd(self) -> float:
        if self.replacements_found == 0:
            return 0.0
        return round(self.total_api_cost_usd / self.replacements_found, 6)

    @classmethod
    def from_economics_list(
        cls, batch_id: str, economics: List[AgentEconomics]
    ) -> "ValueProofReceipt":
        receipt = cls(batch_id=batch_id)
        receipt.contacts_processed = len(economics)

        for econ in economics:
            receipt.total_api_cost_usd += econ.total_api_cost_usd
            receipt.total_tokens_used += econ.tokens_used
            receipt.total_labor_hours_saved += econ.labor_hours_saved
            receipt.total_value_generated_usd += econ.estimated_value_generated_usd

            if econ.verified:
                receipt.contacts_verified_active += 1
            if econ.replacement_found:
                receipt.replacements_found += 1
                receipt.contacts_marked_inactive += 1
            if econ.flagged_for_review:
                receipt.flagged_for_review += 1

        # Outcome-based billing simulation
        receipt.simulated_invoice_usd = round(
            receipt.contacts_processed * BILLED_RATE_PER_VERIFICATION_USD
            + receipt.replacements_found * BILLED_RATE_PER_REPLACEMENT_USD,
            2,
        )

        # Round totals
        receipt.total_api_cost_usd = round(receipt.total_api_cost_usd, 6)
        receipt.total_labor_hours_saved = round(receipt.total_labor_hours_saved, 2)
        receipt.total_value_generated_usd = round(receipt.total_value_generated_usd, 2)

        return receipt

    def format_receipt(self) -> str:
        """Generate the human-readable Value-Proof Receipt string."""
        return (
            f"Batch Complete: {self.contacts_processed} Contacts Processed. "
            f"{self.replacements_found} Replacements Found. "
            f"Total API Cost: ${self.total_api_cost_usd:.4f}. "
            f"SDR Time Saved: {self.total_labor_hours_saved:.1f} hours. "
            f"Estimated Value Generated: ${self.total_value_generated_usd:.2f}. "
            f"Net ROI for this run: +{self.net_roi_percentage:,.0f}%."
        )
