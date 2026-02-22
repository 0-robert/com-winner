"""
ProcessBatchUseCase - Top-level orchestrator.

Pulls contacts from the repository, runs VerifyContactUseCase on each,
writes results back to Supabase, and generates the Value-Proof Receipt.
"""

import asyncio
import logging
import time
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

_SEP = "=" * 70


@dataclass
class ProcessBatchRequest:
    tier: str = "free"
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
    - Computes and persists the Value-Proof Receipt
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
        batch_id = request.batch_id
        wall_start = time.time()

        logger.info(_SEP)
        logger.info(f"[Batch:{batch_id[:8]}] *** BATCH RUN STARTING ***")
        logger.info(
            f"[Batch:{batch_id[:8]}] tier={request.tier!r} | "
            f"limit={request.limit} | concurrency={request.concurrency}"
        )
        logger.info(_SEP)

        # ── Load contacts ─────────────────────────────────────────────────
        contacts = await self.repository.get_contacts_for_verification(
            limit=request.limit
        )
        total = len(contacts)
        logger.info(f"[Batch:{batch_id[:8]}] Loaded {total} contacts from database")

        if total == 0:
            logger.warning(
                f"[Batch:{batch_id[:8]}] No contacts eligible for verification — "
                "check that contacts exist and none are opted-out or already flagged."
            )

        # ── Bounded concurrent verification ────────────────────────────────
        semaphore = asyncio.Semaphore(request.concurrency)
        results: List[VerificationResult] = []
        errors: List[str] = []
        completed_count = 0
        count_lock = asyncio.Lock()

        async def verify_one(contact: Contact, idx: int) -> None:
            nonlocal completed_count
            async with semaphore:
                agent_wall = time.time()
                logger.info(
                    f"[Batch:{batch_id[:8]}] [{idx + 1}/{total}] "
                    f"AGENT STARTING → {contact.name!r} | "
                    f"{contact.title!r} @ {contact.organization!r} | "
                    f"id={contact.id}"
                )

                try:
                    result = await self.verify.execute(
                        VerifyContactRequest(contact=contact, tier=request.tier)
                    )
                    results.append(result)
                    await self._apply_result(contact, result)

                    elapsed = time.time() - agent_wall
                    async with count_lock:
                        completed_count += 1
                        done = completed_count

                    replacement_tag = (
                        f"replacement={result.replacement_name!r}"
                        if result.has_replacement
                        else "no-replacement"
                    )
                    logger.info(
                        f"[Batch:{batch_id[:8]}] [{done}/{total}] "
                        f"AGENT DONE ✓ → {contact.name!r} | "
                        f"status={result.status.value} | "
                        f"{replacement_tag} | "
                        f"flagged={result.needs_human_review} | "
                        f"cost=${result.economics.total_api_cost_usd:.5f} | "
                        f"tokens={result.economics.tokens_used} | "
                        f"elapsed={elapsed:.2f}s"
                    )

                except Exception as exc:
                    elapsed = time.time() - agent_wall
                    async with count_lock:
                        completed_count += 1
                        done = completed_count

                    logger.error(
                        f"[Batch:{batch_id[:8]}] [{done}/{total}] "
                        f"AGENT ERROR ✗ → {contact.name!r} @ {contact.organization!r} | "
                        f"error={exc!r} | elapsed={elapsed:.2f}s",
                        exc_info=True,
                    )
                    errors.append(f"{contact.id} ({contact.name}): {exc}")

        await asyncio.gather(*[verify_one(c, i) for i, c in enumerate(contacts)])

        # ── Generate Value-Proof Receipt ───────────────────────────────────
        economics_list = [r.economics for r in results]
        roi_response = self.roi.execute(
            CalculateROIRequest(
                economics_list=economics_list,
                batch_id=batch_id,
            )
        )
        receipt = roi_response.receipt

        # ── Persist receipt to database (was missing — now fixed) ──────────
        try:
            await self.repository.save_batch_receipt(receipt)
            logger.info(
                f"[Batch:{batch_id[:8]}] Receipt persisted to batch_receipts table OK"
            )
        except Exception as exc:
            logger.error(
                f"[Batch:{batch_id[:8]}] FAILED to save receipt to DB: {exc!r}",
                exc_info=True,
            )

        # ── Final summary ──────────────────────────────────────────────────
        total_elapsed = time.time() - wall_start
        logger.info(_SEP)
        logger.info(f"[Batch:{batch_id[:8]}] *** BATCH RUN COMPLETE ***")
        logger.info(f"[Batch:{batch_id[:8]}] {receipt.format_receipt()}")
        logger.info(
            f"[Batch:{batch_id[:8]}] "
            f"total_elapsed={total_elapsed:.2f}s | "
            f"successes={len(results)} | "
            f"errors={len(errors)}"
        )
        if errors:
            logger.error(f"[Batch:{batch_id[:8]}] ── ERROR SUMMARY ──")
            for err in errors:
                logger.error(f"[Batch:{batch_id[:8]}]   {err}")
        logger.info(_SEP)

        return ProcessBatchResponse(
            batch_id=batch_id,
            receipt=receipt,
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
        logger.debug(
            f"[Batch] save_contact OK: {contact.name!r} → status={contact.status.value}"
        )

        # Persist verification audit record
        await self.repository.save_verification_result(result)
        logger.debug(f"[Batch] save_verification_result OK: contact_id={contact.id}")

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
                f"[Batch] Inserted replacement contact: {replacement.name!r} "
                f"@ {replacement.organization!r} | new_id={replacement.id}"
            )
