"""
SupabaseAdapter - Implements IDataRepository.
Uses the supabase-py client to read/write contact records via PostgREST.
Follows Supabase best practices: typed queries, RLS-aware, connection pooling via env.
"""

import logging
from typing import List, Optional
from datetime import datetime

from supabase import create_client, Client

from ..domain.entities.contact import Contact, ContactStatus
from ..domain.entities.verification_result import VerificationResult
from ..domain.interfaces.i_data_repository import IDataRepository

logger = logging.getLogger(__name__)


def _parse_iso(date_str: Optional[str]) -> datetime:
    if not date_str:
        return datetime.utcnow()
    # Python 3.9 fromisoformat doesn't handle 'Z' well
    if date_str.endswith("Z"):
        date_str = date_str[:-1]
    # It also struggles with timezone info like +00:00 sometimes
    if "+" in date_str:
        date_str = date_str.split("+")[0]
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        return datetime.utcnow()


def _row_to_contact(row: dict) -> Contact:
    return Contact(
        id=row["id"],
        name=row["name"],
        email=row.get("email", ""),
        title=row.get("title", ""),
        organization=row.get("organization", ""),
        status=ContactStatus(row.get("status", "unknown")),
        needs_human_review=row.get("needs_human_review", False),
        review_reason=row.get("review_reason"),
        district_website=row.get("district_website"),
        linkedin_url=row.get("linkedin_url"),
        email_hash=row.get("email_hash"),
        created_at=_parse_iso(row.get("created_at")),
        updated_at=_parse_iso(row.get("updated_at")),
    )


def _contact_to_row(contact: Contact) -> dict:
    return {
        "id": contact.id,
        "name": contact.name,
        "email": contact.email,
        "title": contact.title,
        "organization": contact.organization,
        "status": contact.status.value,
        "needs_human_review": contact.needs_human_review,
        "review_reason": contact.review_reason,
        "district_website": contact.district_website,
        "linkedin_url": contact.linkedin_url,
        "email_hash": contact.email_hash,
        "updated_at": contact.updated_at.isoformat(),
    }


class SupabaseAdapter(IDataRepository):
    """
    PostgreSQL adapter via Supabase PostgREST.
    Best practice: Use service role key for backend operations.
    """

    def __init__(self, url: str, key: str):
        self.client: Client = create_client(url, key)

    async def get_all_contacts(self) -> List[Contact]:
        response = self.client.table("contacts").select("*").neq("status", "opted_out").execute()
        return [_row_to_contact(r) for r in response.data]

    async def get_contacts_for_verification(self, limit: int = 50) -> List[Contact]:
        response = (
            self.client.table("contacts")
            .select("*")
            .neq("status", "opted_out")
            .eq("needs_human_review", False)
            .limit(limit)
            .execute()
        )
        return [_row_to_contact(r) for r in response.data]

    async def get_contacts_needing_review(self) -> List[Contact]:
        response = (
            self.client.table("contacts")
            .select("*")
            .eq("needs_human_review", True)
            .execute()
        )
        return [_row_to_contact(r) for r in response.data]

    async def get_contact_by_id(self, contact_id: str) -> Optional[Contact]:
        response = (
            self.client.table("contacts").select("*").eq("id", contact_id).execute()
        )
        if response.data:
            return _row_to_contact(response.data[0])
        return None

    async def save_contact(self, contact: Contact) -> Contact:
        row = _contact_to_row(contact)
        self.client.table("contacts").upsert(row).execute()
        return contact

    async def save_verification_result(self, result: VerificationResult) -> None:
        row = {
            "contact_id": result.contact_id,
            "status": result.status.value,
            "low_confidence_flag": result.low_confidence_flag,
            "replacement_name": result.replacement_name,
            "replacement_email": result.replacement_email,
            "replacement_title": result.replacement_title,
            "evidence_urls": result.evidence_urls,
            "notes": result.notes,
            "api_cost_usd": result.economics.total_api_cost_usd,
            "tokens_used": result.economics.tokens_used,
            "labor_hours_saved": result.economics.labor_hours_saved,
            "value_generated_usd": result.economics.estimated_value_generated_usd,
            "highest_tier_used": result.economics.highest_tier_used,
            "verified_at": datetime.utcnow().isoformat(),
        }
        self.client.table("verification_results").insert(row).execute()

    async def bulk_update_contacts(self, contacts: List[Contact]) -> None:
        rows = [_contact_to_row(c) for c in contacts]
        self.client.table("contacts").upsert(rows).execute()

    async def insert_contact(self, contact: Contact) -> Contact:
        row = _contact_to_row(contact)
        row["created_at"] = contact.created_at.isoformat()
        self.client.table("contacts").insert(row).execute()
        return contact
