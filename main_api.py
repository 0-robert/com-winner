"""
ProspectKeeper — Unified FastAPI Backend
========================================
Merges all adapters into a single server:
  - LinkedIn scraper      (NoDriverAdapter)
  - Email sender          (EmailSenderAdapter)
  - Contacts CRUD         (SupabaseAdapter)
  - Inbound email webhook (ProcessInboundEmailUseCase)

Start:
    uvicorn main_api:app --reload --port 8000

Interactive docs:
    http://localhost:8000/docs
"""

import asyncio
import base64
import hashlib
import json
import logging
import os
import uuid
from datetime import datetime
from typing import List, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Langfuse config ────────────────────────────────────────────────────────────
_LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
_LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
_LANGFUSE_BASE_URL = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")
_SONNET_INPUT_COST_PER_TOKEN = 3.0 / 1_000_000
_SONNET_OUTPUT_COST_PER_TOKEN = 15.0 / 1_000_000

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="ProspectKeeper API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Dependency-injection container (initialised at startup) ───────────────────

_container = None
_startup_error: Optional[str] = None


@app.on_event("startup")
async def startup():
    global _container, _startup_error
    try:
        from prospectkeeper.infrastructure.config import Config
        from prospectkeeper.infrastructure.container import Container

        _container = Container(Config.from_env())
        logger.info("Container initialised successfully.")
    except Exception as e:
        _startup_error = str(e)
        logger.error(f"Container startup failed: {e}")


def get_container():
    if _startup_error:
        raise HTTPException(status_code=503, detail=f"Service misconfigured: {_startup_error}")
    if _container is None:
        raise HTTPException(status_code=503, detail="Service not ready.")
    return _container


# ── Auth ──────────────────────────────────────────────────────────────────────

_API_KEY = os.getenv("API_KEY", "dev-key")


def _auth(x_api_key: str = Header(...)) -> None:
    if x_api_key != _API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


# ── Request / Response models ─────────────────────────────────────────────────


class ContactIn(BaseModel):
    id: Optional[str] = None
    name: str
    email: Optional[str] = ""
    title: Optional[str] = ""
    organization: str
    linkedin_url: Optional[str] = None
    district_website: Optional[str] = None
    status: Optional[str] = "unknown"
    needs_human_review: Optional[bool] = False
    review_reason: Optional[str] = None


class ScrapeRequest(BaseModel):
    linkedin_url: str
    contact_name: str
    organization: Optional[str] = None
    contact_id: Optional[str] = None  # If provided, snapshot is saved to DB


class SendOneRequest(BaseModel):
    contact_id: str


class SendAllRequest(BaseModel):
    limit: Optional[int] = 500
    concurrency: Optional[int] = 5


class InboundEmailRequest(BaseModel):
    sender_email: str
    body: str
    subject: Optional[str] = ""


class BatchRunRequest(BaseModel):
    tier: str = "free"
    limit: int = 50
    concurrency: int = 5


# ── Health ────────────────────────────────────────────────────────────────────


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok", "error": _startup_error}


# ── Contacts CRUD ─────────────────────────────────────────────────────────────


@app.get("/contacts", tags=["contacts"])
async def list_contacts(_: None = Depends(_auth)):
    """Return all non-opted-out contacts, enriched with LinkedIn freshness data."""
    c = get_container()
    contacts = await c.repository.get_all_contacts()
    freshness = await c.repository.get_all_linkedin_freshness()

    result = []
    for contact in contacts:
        if contact.status.value == "opted_out":
            continue
        row = {
            "id": contact.id,
            "name": contact.name,
            "email": contact.email,
            "title": contact.title,
            "organization": contact.organization,
            "status": contact.status.value,
            "needs_human_review": contact.needs_human_review,
            "review_reason": contact.review_reason,
            "linkedin_url": contact.linkedin_url,
            "district_website": contact.district_website,
            "last_scraped_at": None,
            "last_changed_at": None,
        }
        if contact.id in freshness:
            f = freshness[contact.id]
            row["last_scraped_at"] = f.get("last_scraped_at")
            row["last_changed_at"] = f.get("last_changed_at")
        result.append(row)

    return result


@app.post("/contacts", status_code=status.HTTP_201_CREATED, tags=["contacts"])
async def create_contact(body: ContactIn, _: None = Depends(_auth)):
    """Insert a new contact. Frontend generates the UUID."""
    from prospectkeeper.domain.entities.contact import Contact, ContactStatus

    c = get_container()
    contact = Contact(
        id=body.id or str(uuid.uuid4()),
        name=body.name,
        email=body.email or "",
        title=body.title or "",
        organization=body.organization,
        status=ContactStatus(body.status or "unknown"),
        needs_human_review=body.needs_human_review or False,
        district_website=body.district_website,
        linkedin_url=body.linkedin_url,
    )
    saved = await c.repository.insert_contact(contact)
    return {"id": saved.id, "name": saved.name}


@app.put("/contacts", tags=["contacts"])
async def update_contact(body: ContactIn, _: None = Depends(_auth)):
    """Update editable fields on an existing contact."""
    from prospectkeeper.domain.entities.contact import ContactStatus

    if not body.id:
        raise HTTPException(status_code=400, detail="id is required")

    c = get_container()
    contact = await c.repository.get_contact_by_id(body.id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    contact.name = body.name
    contact.email = body.email or ""
    contact.title = body.title or ""
    contact.organization = body.organization
    contact.linkedin_url = body.linkedin_url
    contact.district_website = body.district_website

    if body.status:
        contact.status = ContactStatus(body.status)
    if body.needs_human_review is not None:
        contact.needs_human_review = body.needs_human_review
    # Clear review_reason when un-flagging
    if body.needs_human_review is False:
        contact.review_reason = None
    elif body.review_reason is not None:
        contact.review_reason = body.review_reason

    saved = await c.repository.save_contact(contact)
    return {
        "id": saved.id,
        "name": saved.name,
        "email": saved.email,
        "title": saved.title,
        "organization": saved.organization,
        "status": saved.status.value,
        "needs_human_review": saved.needs_human_review,
        "review_reason": saved.review_reason,
        "linkedin_url": saved.linkedin_url,
        "district_website": saved.district_website,
    }


@app.delete("/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["contacts"])
async def delete_contact(contact_id: str, _: None = Depends(_auth)):
    """Permanently delete a contact."""
    c = get_container()
    deleted = await c.repository.delete_contact(contact_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Contact not found")


@app.get("/contacts/{contact_id}/linkedin-change", tags=["contacts"])
async def get_linkedin_change(contact_id: str, _: None = Depends(_auth)):
    """
    Return the field-level diff from the most recent LinkedIn snapshot
    where data actually changed. Returns {} if no changes on record.
    """
    c = get_container()
    row = await c.repository.get_latest_change_summary(contact_id)
    if not row:
        return {}
    # change_summary is a JSONB column: {title_from, title_to, org_from, ...}
    return row.get("change_summary") or {}


# ── LinkedIn Scrape ───────────────────────────────────────────────────────────


def _profile_hash(title: Optional[str], org: Optional[str], headline: Optional[str]) -> str:
    key = json.dumps({"title": title, "org": org, "headline": headline}, sort_keys=True)
    return hashlib.md5(key.encode()).hexdigest()


@app.post("/scrape", tags=["linkedin"])
async def scrape_linkedin(req: ScrapeRequest, _: None = Depends(_auth)):
    """
    Scrape a LinkedIn profile via NoDriverAdapter.

    If contact_id is provided:
      - Compares against the previous snapshot (hash-based change detection)
      - Saves a new linkedin_snapshots row
      - Updates the contact's status/title in the contacts table
    """
    c = get_container()

    result = await c.linkedin.verify_employment(
        linkedin_url=req.linkedin_url,
        contact_name=req.contact_name,
        organization=req.organization or "",
    )

    resp = {
        "success": result.success,
        "blocked": result.blocked,
        "error": result.error,
        "still_at_organization": result.still_at_organization,
        "current_title": result.current_title,
        "current_organization": result.current_organization,
        "name": result.name,
        "headline": result.headline,
        "location": result.location,
        "experience": result.experience or [],
        "education": result.education or [],
        "skills": result.skills or [],
        "employment_confidence": 0.9 if result.still_at_organization else 0.3,
        "data_changed": False,
        "last_scraped_at": None,
        "last_changed_at": None,
    }

    if not result.success or not req.contact_id:
        return resp

    # ── Persist snapshot and update contact ───────────────────────────────
    now = datetime.utcnow().isoformat()
    new_hash = _profile_hash(result.current_title, result.current_organization, result.headline)

    old_snap = await c.repository.get_latest_linkedin_snapshot(req.contact_id)
    data_changed = (old_snap is None) or (old_snap.get("profile_hash") != new_hash)

    change_summary = {}
    if data_changed and old_snap:
        change_summary = {
            "title_from": old_snap.get("current_title"),
            "title_to": result.current_title,
            "org_from": old_snap.get("current_org"),
            "org_to": result.current_organization,
            "headline_from": old_snap.get("headline"),
            "headline_to": result.headline,
        }

    await c.repository.save_linkedin_snapshot({
        "contact_id": req.contact_id,
        "profile_hash": new_hash,
        "current_title": result.current_title,
        "current_org": result.current_organization,
        "headline": result.headline,
        "scraped_at": now,
        "data_changed": data_changed,
        "change_summary": change_summary,
    })

    # Update contact status based on scrape result
    if result.still_at_organization is not None:
        contact = await c.repository.get_contact_by_id(req.contact_id)
        if contact:
            if result.still_at_organization:
                contact.mark_active()
                if result.current_title:
                    contact.title = result.current_title
            else:
                contact.flag_for_review("LinkedIn: no longer at organisation")
            await c.repository.save_contact(contact)

    resp["data_changed"] = data_changed
    resp["last_scraped_at"] = now
    resp["last_changed_at"] = now if data_changed else (old_snap or {}).get("scraped_at")
    return resp


# ── Email ─────────────────────────────────────────────────────────────────────


@app.post("/email/send-one", tags=["email"])
async def send_one_email(req: SendOneRequest, _: None = Depends(_auth)):
    """Send an info-review confirmation email to a single contact."""
    c = get_container()

    contact = await c.repository.get_contact_by_id(req.contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    if contact.is_opted_out():
        raise HTTPException(status_code=400, detail="Contact has opted out — cannot send email")

    result = await c.email_sender.send_confirmation(contact)
    return {"success": result.success, "email": result.email, "error": result.error}


@app.post("/email/send-all", tags=["email"])
async def send_all_emails(req: SendAllRequest, _: None = Depends(_auth)):
    """
    Send info-review emails to all eligible contacts (not opted-out, has email).
    Respects the concurrency limit to avoid rate-limiting Resend.
    """
    c = get_container()

    contacts = await c.repository.get_all_contacts()
    eligible = [ct for ct in contacts if not ct.is_opted_out() and ct.email][: req.limit]
    logger.info(f"[email/send-all] Sending to {len(eligible)} contacts")

    total_sent = 0
    total_failed = 0
    semaphore = asyncio.Semaphore(req.concurrency)

    async def _send(contact):
        nonlocal total_sent, total_failed
        async with semaphore:
            res = await c.email_sender.send_confirmation(contact)
            if res.success:
                total_sent += 1
            else:
                total_failed += 1
                logger.warning(f"[email/send-all] Failed: {contact.email} — {res.error}")

    await asyncio.gather(*[_send(ct) for ct in eligible])
    return {"total_sent": total_sent, "total_failed": total_failed}


# ── Inbound Email Webhook (Zapier → Resend reply-to) ─────────────────────────


@app.post("/inbound-email", tags=["email"])
async def inbound_email(req: InboundEmailRequest, _: None = Depends(_auth)):
    """
    Zapier/webhook endpoint. Receives a contact's email reply, parses it with
    Claude Haiku, and updates their record with any corrected information.
    """
    c = get_container()

    result = await c.process_inbound_email_use_case.execute(
        sender_email=req.sender_email,
        email_body=req.body,
        subject=req.subject,
    )
    return {
        "success": result.success,
        "contact_id": result.contact_id,
        "fields_updated": result.fields_updated,
        "error": result.error,
    }


# ── Langfuse Stats (stub — returns not_configured until Langfuse is wired) ────


@app.get("/langfuse-stats", tags=["observability"])
async def langfuse_stats(_: None = Depends(_auth)):
    """Query the Langfuse REST API and return aggregated token/cost stats."""
    if not _LANGFUSE_PUBLIC_KEY or not _LANGFUSE_SECRET_KEY:
        return {
            "not_configured": True,
            "total_calls": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "avg_cost_per_call": 0.0,
            "recent": [],
            "langfuse_dashboard_url": "",
        }

    auth_header = "Basic " + base64.b64encode(
        f"{_LANGFUSE_PUBLIC_KEY}:{_LANGFUSE_SECRET_KEY}".encode()
    ).decode()

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{_LANGFUSE_BASE_URL}/api/public/observations",
                params={"type": "GENERATION", "limit": 50},
                headers={"Authorization": auth_header},
            )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not reach Langfuse: {e}")

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Langfuse API returned {resp.status_code}")

    data = resp.json()
    observations = data.get("data", [])
    total_pages_items = data.get("meta", {}).get("totalItems", len(observations))

    total_input = total_output = 0
    total_cost = 0.0
    recent = []

    for obs in observations:
        usage = obs.get("usage") or {}
        inp = usage.get("input") or 0
        out = usage.get("output") or 0
        cost = obs.get("calculatedTotalCost")
        if cost is None:
            cost = inp * _SONNET_INPUT_COST_PER_TOKEN + out * _SONNET_OUTPUT_COST_PER_TOKEN
        total_input += inp
        total_output += out
        total_cost += cost
        if len(recent) < 10:
            recent.append({
                "name": obs.get("name"),
                "model": obs.get("model"),
                "input_tokens": inp,
                "output_tokens": out,
                "cost_usd": round(cost, 6),
                "start_time": obs.get("startTime"),
            })

    n = len(observations)
    return {
        "total_calls": total_pages_items,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_tokens": total_input + total_output,
        "total_cost_usd": round(total_cost, 6),
        "avg_cost_per_call": round(total_cost / n, 6) if n > 0 else 0.0,
        "recent": recent,
        "langfuse_dashboard_url": _LANGFUSE_BASE_URL,
    }


# ── Agent — SSE streaming agentic verification ────────────────────────────────


@app.post("/agent/verify/{contact_id}", tags=["agent"])
async def agent_verify(contact_id: str, _: None = Depends(_auth)):
    """
    Launch the Claude tool_use agent for a single contact.
    Streams Server-Sent Events: start / thinking / tool_call / tool_result / final / done.
    """
    from prospectkeeper.use_cases.verify_contact_agent import VerifyContactAgentUseCase

    c = get_container()
    agent = VerifyContactAgentUseCase(
        repository=c.repository,
        scraper=c.scraper,
        linkedin=c.linkedin,
        email_sender=c.email_sender,
    )

    async def event_stream():
        async for event in agent.execute(contact_id):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Config status ─────────────────────────────────────────────────────────────


@app.get("/config-status", tags=["meta"])
async def config_status(_: None = Depends(_auth)):
    """Return which API keys are configured and current batch settings."""
    return {
        "anthropic_configured": bool(os.getenv("ANTHROPIC_API_KEY")),
        "supabase_configured": bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_KEY")),
        "langfuse_configured": bool(os.getenv("LANGFUSE_SECRET_KEY") and os.getenv("LANGFUSE_PUBLIC_KEY")),
        "zerobounce_configured": bool(os.getenv("ZEROBOUNCE_API_KEY")),
        "resend_configured": bool(os.getenv("RESEND_API_KEY")),
        "batch_limit": int(os.getenv("BATCH_LIMIT", 50)),
        "batch_concurrency": int(os.getenv("BATCH_CONCURRENCY", 5)),
    }


# ── Batch receipts ────────────────────────────────────────────────────────────


@app.get("/batch-receipts", tags=["batch"])
async def get_batch_receipts(limit: int = 10, _: None = Depends(_auth)):
    """Return the most recent batch run receipts (skips empty runs with 0 contacts)."""
    c = get_container()
    response = (
        c.repository.client.table("batch_receipts")
        .select("*")
        .gt("contacts_processed", 0)
        .order("run_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data


# ── Contacts — review queue ───────────────────────────────────────────────────


@app.get("/contacts/review", tags=["contacts"])
async def contacts_for_review(_: None = Depends(_auth)):
    """Return contacts flagged for human review."""
    c = get_container()
    contacts = await c.repository.get_all_contacts()
    return [
        {
            "id": ct.id,
            "name": ct.name,
            "email": ct.email,
            "title": ct.title,
            "organization": ct.organization,
            "status": ct.status.value,
            "needs_human_review": ct.needs_human_review,
            "review_reason": ct.review_reason,
            "linkedin_url": ct.linkedin_url,
            "district_website": ct.district_website,
        }
        for ct in contacts
        if ct.needs_human_review
    ]


# ── Batch run trigger — streams SSE progress ─────────────────────────────────


@app.post("/batch/run", tags=["batch"])
async def trigger_batch(req: BatchRunRequest, _: None = Depends(_auth)):
    """
    Stream real-time batch verification progress via Server-Sent Events.
    Emits: batch_start, contact_start, contact_done, contact_error, batch_complete.
    """
    from prospectkeeper.use_cases.process_batch import ProcessBatchRequest

    batch_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()

    logger.info(
        f"[API] /batch/run SSE stream opened | batch_id={batch_id} "
        f"tier={req.tier!r} limit={req.limit} concurrency={req.concurrency}"
    )

    async def _run():
        try:
            c = get_container()
            await c.process_batch_use_case.execute(
                ProcessBatchRequest(
                    tier=req.tier,
                    limit=req.limit,
                    concurrency=req.concurrency,
                    batch_id=batch_id,
                ),
                event_callback=queue.put,
            )
        except Exception as e:
            logger.error(f"[API] Batch run FAILED | batch_id={batch_id} | error={e!r}", exc_info=True)
            await queue.put({"type": "error", "message": str(e)})
        finally:
            await queue.put(None)  # sentinel — closes the stream

    asyncio.create_task(_run())

    async def event_stream():
        while True:
            event = await queue.get()
            if event is None:
                break
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
