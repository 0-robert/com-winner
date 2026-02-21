"""
ProcessBatchUseCase - Top-level orchestrator.

Pulls contacts from the repository, runs VerifyContactUseCase on each,
writes results back to Supabase, and generates the Value-Proof Receipt.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import List, Optional

from ..domain.entities.contact import Contact, ContactStatus
from ..domain.entities.agent_economics import AgentEconomics, ValueProofReceipt
from ..domain.entities.verification_result import VerificationResult
from ..domain.interfaces.i_data_repository import IDataRepository
from .verify_contact import VerifyContactUseCase, VerifyContactRequest
from .calculate_roi import CalculateROIUseCase, CalculateROIRequest

logger = logging.getLogger(__name__)


@dataclass
class ProcessBatchRequest:
    limit: int = 50
    batch_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    concurrency: int = 5  # Max parallel verifications


@dataclass
class ProcessBatchResponse:
    batch_id: str
    receipt: ValueProofReceipt
    results: List[VerificationResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class ProcessBatchUseCase:
    """
    Orchestrates a full batch verification run.
    - Reads contacts from the repository
    - Verifies each contact (with bounded concurrency)
    - Writes updated contacts and results back to DB
    - Computes and returns the Value-Proof Receipt
    """

    def __init__(
        self,
        repository: IDataRepository,
        verify_use_case: VerifyContactUseCase,
        roi_use_case: CalculateROIUseCase,
    ):
        self.repository = repository
        self.verify = verify_use_case
        self.roi = roi_use_case

    async def execute(self, request: ProcessBatchRequest) -> ProcessBatchResponse:
        logger.info(
            f"[Batch {request.batch_id}] Starting batch run — limit={request.limit}"
        )

        contacts = await self.repository.get_contacts_for_verification(
            limit=request.limit
        )
        logger.info(f"[Batch {request.batch_id}] {len(contacts)} contacts loaded")

        # Bounded concurrent verification
        semaphore = asyncio.Semaphore(request.concurrency)
        results: List[VerificationResult] = []
        errors: List[str] = []

        async def verify_one(contact: Contact):
            async with semaphore:
                try:
                    result = await self.verify.execute(
                        VerifyContactRequest(contact=contact)
                    )
                    results.append(result)
                    await self._apply_result(contact, result)
                except Exception as e:
                    logger.error(f"[Batch] Error verifying {contact.id}: {e}")
                    errors.append(f"{contact.id}: {e}")

        await asyncio.gather(*[verify_one(c) for c in contacts])

        # Generate Value-Proof Receipt
        economics_list = [r.economics for r in results]
        roi_response = self.roi.execute(
            CalculateROIRequest(
                economics_list=economics_list,
                batch_id=request.batch_id,
            )
        )

        logger.info(
            f"[Batch {request.batch_id}] Complete. "
            f"{roi_response.receipt.format_receipt()}"
        )

        return ProcessBatchResponse(
            batch_id=request.batch_id,
            receipt=roi_response.receipt,
            results=results,
            errors=errors,
        )

    async def _apply_result(
        self, contact: Contact, result: VerificationResult
    ) -> None:
        """Apply verification result back to the contact entity and persist."""
        # Update contact status
        if result.status == ContactStatus.ACTIVE:
            contact.mark_active()
        elif result.status == ContactStatus.INACTIVE:
            contact.mark_inactive()

        # Flag for review if needed
        if result.needs_human_review:
            contact.flag_for_review(result.notes or "Needs review")

        # Persist updated contact
        await self.repository.save_contact(contact)

        # Persist verification audit record
        await self.repository.save_verification_result(result)

        # If a replacement was found, insert new contact
        if result.has_replacement:
            replacement = Contact.create(
                name=result.replacement_name,
                email=result.replacement_email or "",
                title=result.replacement_title or contact.title,
                organization=contact.organization,
                district_website=contact.district_website,
            )
            await self.repository.insert_contact(replacement)
            logger.info(
                f"[Batch] Inserted replacement contact: {replacement.name} "
                f"@ {replacement.organization}"
            )
