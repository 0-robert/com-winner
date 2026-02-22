"""
Supabase API Connector — FastAPI Service
===================================
Wraps SupabaseAdapter as an HTTP API so any service can interact with the
database without importing the adapter directly or using supabase-py.

Start:
    uvicorn supabase_api:app --reload --port 8002

Authentication:
    Pass the API key in the X-API-Key header.
    Set the key via the SUPABASE_API_KEY environment variable (defaults to
    "dev-key" when unset).
"""

import logging
import os
import sys
from typing import List, Optional
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

# ── Bootstrap ──────────────────────────────────────────────────────────────
load_dotenv()

# Ensure the project root is on sys.path when the file is run directly
sys.path.insert(0, os.path.dirname(__file__))

from prospectkeeper.adapters.supabase_adapter import SupabaseAdapter
from prospectkeeper.domain.entities.contact import Contact, ContactStatus
from prospectkeeper.domain.entities.verification_result import VerificationResult
from prospectkeeper.domain.entities.agent_economics import AgentEconomics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── API key guard ──────────────────────────────────────────────────────────
_API_KEY = os.environ.get("SUPABASE_API_KEY", "dev-key")

def _require_api_key(x_api_key: str = Header(..., description="Service API key")) -> None:
    if x_api_key != _API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )

# ── App ────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Supabase Connector API",
    description="Microservice wrapper for ProspectKeeper's Supabase adapter.",
    version="1.0.0",
)

# ── Adapter Initialization ─────────────────────────────────────────────────
supabase_url = os.environ.get("SUPABASE_URL", "")
supabase_key = os.environ.get("SUPABASE_SERVICE_KEY", "")

if not supabase_url or not supabase_key:
    logger.warning("SUPABASE_URL or SUPABASE_SERVICE_KEY not set. API calls will fail.")
    # Initialize with dummy values so the app starts, but calls will fail later
    _adapter = SupabaseAdapter("https://dummy.supabase.co", "dummy-key")
else:
    _adapter = SupabaseAdapter(supabase_url, supabase_key)

# ── Pydantic Schemas ───────────────────────────────────────────────────────

class ContactSchema(BaseModel):
    id: str
    name: str
    email: str = ""
    title: str = ""
    organization: str
    status: str = "unknown"
    needs_human_review: bool = False
    review_reason: Optional[str] = None
    district_website: Optional[str] = None
    linkedin_url: Optional[str] = None
    email_hash: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # LinkedIn freshness (populated from contact_linkedin_freshness view)
    last_scraped_at: Optional[datetime] = None
    last_changed_at: Optional[datetime] = None

    def to_domain(self) -> Contact:
        status_enum = ContactStatus(self.status) if self.status else ContactStatus.UNKNOWN
        return Contact(
            id=self.id,
            name=self.name,
            email=self.email,
            title=self.title,
            organization=self.organization,
            status=status_enum,
            needs_human_review=self.needs_human_review,
            review_reason=self.review_reason,
            district_website=self.district_website,
            linkedin_url=self.linkedin_url,
            email_hash=self.email_hash,
            created_at=self.created_at or datetime.utcnow(),
            updated_at=self.updated_at or datetime.utcnow(),
        )

    @classmethod
    def from_domain(cls, contact: Contact) -> "ContactSchema":
        return cls(
            id=contact.id,
            name=contact.name,
            email=contact.email,
            title=contact.title,
            organization=contact.organization,
            status=contact.status.value if contact.status else "unknown",
            needs_human_review=contact.needs_human_review,
            review_reason=contact.review_reason,
            district_website=contact.district_website,
            linkedin_url=contact.linkedin_url,
            email_hash=contact.email_hash,
            created_at=contact.created_at,
            updated_at=contact.updated_at,
        )

class AgentEconomicsSchema(BaseModel):
    contact_id: str
    zerobounce_cost_usd: float = 0.0
    claude_cost_usd: float = 0.0
    tokens_used: int = 0
    verified: bool = False
    replacement_found: bool = False
    flagged_for_review: bool = False
    highest_tier_used: int = 0

    def to_domain(self) -> AgentEconomics:
        return AgentEconomics(
            contact_id=self.contact_id,
            zerobounce_cost_usd=self.zerobounce_cost_usd,
            claude_cost_usd=self.claude_cost_usd,
            tokens_used=self.tokens_used,
            verified=self.verified,
            replacement_found=self.replacement_found,
            flagged_for_review=self.flagged_for_review,
            highest_tier_used=self.highest_tier_used,
        )

class VerificationResultSchema(BaseModel):
    contact_id: str
    status: str
    economics: AgentEconomicsSchema
    replacement_name: Optional[str] = None
    replacement_email: Optional[str] = None
    replacement_title: Optional[str] = None
    low_confidence_flag: bool = False
    current_organization: Optional[str] = None
    evidence_urls: List[str] = Field(default_factory=list)
    notes: Optional[str] = None

    def to_domain(self) -> VerificationResult:
        status_enum = ContactStatus(self.status) if self.status else ContactStatus.UNKNOWN
        return VerificationResult(
            contact_id=self.contact_id,
            status=status_enum,
            economics=self.economics.to_domain(),
            replacement_name=self.replacement_name,
            replacement_email=self.replacement_email,
            replacement_title=self.replacement_title,
            low_confidence_flag=self.low_confidence_flag,
            current_organization=self.current_organization,
            evidence_urls=self.evidence_urls,
            notes=self.notes,
        )

# ── Routes ─────────────────────────────────────────────────────────────────

@app.get("/health", summary="Health check", tags=["Utility"])
async def health() -> dict:
    return {"status": "ok", "supabase_configured": bool(supabase_url and supabase_key)}

@app.get("/contacts", response_model=List[ContactSchema], tags=["Contacts"])
async def get_all_contacts(x_api_key: str = Header(...)):
    _require_api_key(x_api_key)
    contacts = await _adapter.get_all_contacts()
    freshness = await _adapter.get_all_linkedin_freshness()
    result = []
    for c in contacts:
        schema = ContactSchema.from_domain(c)
        f = freshness.get(c.id)
        if f:
            schema.last_scraped_at = f.get("last_scraped_at")
            schema.last_changed_at = f.get("last_changed_at")
        result.append(schema)
    return result

@app.get("/contacts/verify", response_model=List[ContactSchema], tags=["Contacts"])
async def get_contacts_for_verification(limit: int = 50, x_api_key: str = Header(...)):
    _require_api_key(x_api_key)
    contacts = await _adapter.get_contacts_for_verification(limit=limit)
    return [ContactSchema.from_domain(c) for c in contacts]

@app.get("/contacts/review", response_model=List[ContactSchema], tags=["Contacts"])
async def get_contacts_needing_review(x_api_key: str = Header(...)):
    _require_api_key(x_api_key)
    contacts = await _adapter.get_contacts_needing_review()
    return [ContactSchema.from_domain(c) for c in contacts]

@app.get("/contacts/{contact_id}", response_model=ContactSchema, tags=["Contacts"])
async def get_contact_by_id(contact_id: str, x_api_key: str = Header(...)):
    _require_api_key(x_api_key)
    contact = await _adapter.get_contact_by_id(contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return ContactSchema.from_domain(contact)

@app.put("/contacts", response_model=ContactSchema, tags=["Contacts"])
async def save_contact(contact: ContactSchema, x_api_key: str = Header(...)):
    _require_api_key(x_api_key)
    saved = await _adapter.save_contact(contact.to_domain())
    return ContactSchema.from_domain(saved)

@app.post("/contacts", response_model=ContactSchema, tags=["Contacts"])
async def insert_contact(contact: ContactSchema, x_api_key: str = Header(...)):
    _require_api_key(x_api_key)
    inserted = await _adapter.insert_contact(contact.to_domain())
    return ContactSchema.from_domain(inserted)

@app.post("/contacts/bulk", tags=["Contacts"])
async def bulk_update_contacts(contacts: List[ContactSchema], x_api_key: str = Header(...)):
    _require_api_key(x_api_key)
    domain_contacts = [c.to_domain() for c in contacts]
    await _adapter.bulk_update_contacts(domain_contacts)
    return {"status": "success", "updated": len(contacts)}

@app.delete("/contacts/{contact_id}", tags=["Contacts"])
async def delete_contact(contact_id: str, x_api_key: str = Header(...)):
    """Delete a contact by ID."""
    _require_api_key(x_api_key)
    deleted = await _adapter.delete_contact(contact_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Contact not found")
    return {"status": "deleted", "id": contact_id}

@app.get("/contacts/{contact_id}/linkedin-change", tags=["Contacts"])
async def get_linkedin_change(contact_id: str, x_api_key: str = Header(...)):
    """Return the most recent snapshot where data actually changed, with the diff summary."""
    _require_api_key(x_api_key)
    change = await _adapter.get_latest_change_summary(contact_id)
    return change or {}

@app.post("/verification-results", tags=["Verification"])
async def save_verification_result(result: VerificationResultSchema, x_api_key: str = Header(...)):
    _require_api_key(x_api_key)
    await _adapter.save_verification_result(result.to_domain())
    return {"status": "success"}


@app.get("/batch-receipts", tags=["Receipts"])
async def get_batch_receipts(limit: int = 10, x_api_key: str = Header(...)):
    _require_api_key(x_api_key)
    response = (
        _adapter.client.table("batch_receipts")
        .select("*")
        .order("run_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data
