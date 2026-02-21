"""
CalculateROIUseCase - Aggregates economics from a batch run.
Produces the Value-Proof Receipt shown on the dashboard.
"""

import logging
import uuid
from dataclasses import dataclass
from typing import List

from ..domain.entities.agent_economics import AgentEconomics, ValueProofReceipt

logger = logging.getLogger(__name__)


@dataclass
class CalculateROIRequest:
    economics_list: List[AgentEconomics]
    batch_id: str = ""


@dataclass
class CalculateROIResponse:
    receipt: ValueProofReceipt


class CalculateROIUseCase:
    """
    Aggregates per-contact economics into a batch-level Value-Proof Receipt.
    The receipt drives the outcome-based billing simulation.
    """

    def execute(self, request: CalculateROIRequest) -> CalculateROIResponse:
        batch_id = request.batch_id or str(uuid.uuid4())

        receipt = ValueProofReceipt.from_economics_list(
            batch_id=batch_id,
            economics=request.economics_list,
        )

        logger.info(receipt.format_receipt())
        return CalculateROIResponse(receipt=receipt)
