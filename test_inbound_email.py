"""
Standalone test for ProcessInboundEmailUseCase.
Mocks the repository so no Supabase needed — but hits Claude Haiku for real.

Usage:
    python test_inbound_email.py
"""

import asyncio
import os
import json
from datetime import datetime
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv(override=True)

from prospectkeeper.domain.entities.contact import Contact, ContactStatus
from prospectkeeper.domain.entities.verification_result import VerificationResult
from prospectkeeper.domain.interfaces.i_data_repository import IDataRepository
from prospectkeeper.use_cases.process_inbound_email import ProcessInboundEmailUseCase


# ── Fake in-memory repository ────────────────────────────────────────────────

class FakeRepository(IDataRepository):
    """In-memory repo with one seeded contact for testing."""

    def __init__(self):
        self.contacts: dict[str, Contact] = {}
        self._seed()

    def _seed(self):
        c = Contact(
            id="test-001",
            name="Jane Smith",
            email="jane.smith@example.com",
            title="Director of Special Education",
            organization="Springfield Unified School District",
            status=ContactStatus.PENDING_CONFIRMATION,
            needs_human_review=True,
            review_reason="Awaiting email confirmation",
            district_website="https://www.springfieldusd.org",
            linkedin_url=None,
        )
        self.contacts[c.id] = c

    async def get_contact_by_email(self, email: str) -> Optional[Contact]:
        for c in self.contacts.values():
            if c.email.lower() == email.lower():
                return c
        return None

    async def save_contact(self, contact: Contact) -> Contact:
        self.contacts[contact.id] = contact
        return contact

    # ── Stubs (not used in this test) ─────────────────────────────────────
    async def get_all_contacts(self) -> List[Contact]:
        return list(self.contacts.values())

    async def get_contacts_for_verification(self, limit: int = 50) -> List[Contact]:
        return []

    async def get_contacts_needing_review(self) -> List[Contact]:
        return [c for c in self.contacts.values() if c.needs_human_review]

    async def get_contact_by_id(self, contact_id: str) -> Optional[Contact]:
        return self.contacts.get(contact_id)

    async def save_verification_result(self, result: VerificationResult) -> None:
        pass

    async def bulk_update_contacts(self, contacts: List[Contact]) -> None:
        for c in contacts:
            self.contacts[c.id] = c

    async def insert_contact(self, contact: Contact) -> Contact:
        self.contacts[contact.id] = contact
        return contact


# ── Test scenarios ────────────────────────────────────────────────────────────

SCENARIOS = [
    {
        "name": "Contact updates their title and org",
        "sender": "jane.smith@example.com",
        "subject": "Re: Please review the information we have on file for you",
        "body": """Hi there,

Thanks for reaching out. A couple of corrections:

My title is now Assistant Superintendent of Student Services, and I've moved
to Shelby County Schools.

Everything else looks right!

Best,
Jane""",
    },
    {
        "name": "Contact confirms everything is correct",
        "sender": "jane.smith@example.com",
        "subject": "Re: Please review the information we have on file for you",
        "body": """Looks good to me, no changes needed. Thanks!

-- Jane Smith""",
    },
    {
        "name": "Unknown sender (no matching contact)",
        "sender": "nobody@unknown.org",
        "subject": "Re: info review",
        "body": "Here are my updates...",
    },
]


async def run_tests():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set in .env")
        return

    print("=" * 70)
    print("  ProcessInboundEmailUseCase — Live Test (Claude Haiku)")
    print("=" * 70)

    for i, scenario in enumerate(SCENARIOS, 1):
        # Fresh repo each time so the contact resets
        repo = FakeRepository()
        use_case = ProcessInboundEmailUseCase(
            repository=repo,
            anthropic_api_key=api_key,
        )

        print(f"\n{'─' * 70}")
        print(f"  Scenario {i}: {scenario['name']}")
        print(f"{'─' * 70}")
        print(f"  Sender:  {scenario['sender']}")
        print(f"  Subject: {scenario['subject']}")
        print(f"  Body:    {scenario['body'][:80]}...")

        # Snapshot BEFORE
        contact_before = await repo.get_contact_by_email(scenario["sender"])
        if contact_before:
            print(f"\n  BEFORE:")
            print(f"    Name:         {contact_before.name}")
            print(f"    Title:        {contact_before.title}")
            print(f"    Organization: {contact_before.organization}")
            print(f"    Website:      {contact_before.district_website}")
            print(f"    LinkedIn:     {contact_before.linkedin_url}")
            print(f"    Review flag:  {contact_before.needs_human_review}")

        result = await use_case.execute(
            sender_email=scenario["sender"],
            email_body=scenario["body"],
            subject=scenario["subject"],
        )

        print(f"\n  RESULT:")
        print(f"    Success:        {result.success}")
        print(f"    Contact ID:     {result.contact_id}")
        print(f"    Fields updated: {result.fields_updated}")
        if result.error:
            print(f"    Error:          {result.error}")

        if result.parse_result:
            pr = result.parse_result
            print(f"\n  CLAUDE HAIKU OUTPUT:")
            print(f"    Raw parsed:     {json.dumps(pr.all_parsed, indent=2)}")
            print(f"    Updates only:   {json.dumps(pr.updates, indent=2)}")
            print(f"    Tokens:         {pr.tokens_input} in + {pr.tokens_output} out")
            print(f"    Cost:           ${pr.cost_usd:.6f}")

        # Snapshot AFTER
        contact_after = await repo.get_contact_by_email(scenario["sender"])
        if contact_after and result.fields_updated:
            print(f"\n  AFTER:")
            print(f"    Name:         {contact_after.name}")
            print(f"    Title:        {contact_after.title}")
            print(f"    Organization: {contact_after.organization}")
            print(f"    Website:      {contact_after.district_website}")
            print(f"    LinkedIn:     {contact_after.linkedin_url}")
            print(f"    Review flag:  {contact_after.needs_human_review}")

    print(f"\n{'=' * 70}")
    print("  All scenarios complete.")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    asyncio.run(run_tests())
