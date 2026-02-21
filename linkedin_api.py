"""
ProspectKeeper — Unified FastAPI Service
=========================================
Serves both the LinkedIn scraper and outbound email endpoints.
The React frontend proxies all /api/* requests here.

Start:
    uvicorn linkedin_api:app --reload --port 8001

Interactive docs:
    http://localhost:8001/docs   (Swagger UI)
    http://localhost:8001/redoc  (ReDoc)

Authentication:
    Pass the API key in the X-API-Key header.
    Set the key via the LINKEDIN_API_KEY environment variable (defaults to
    "dev-key" when unset so local testing works without configuration).
"""

import asyncio
import base64
import hashlib
import json
import logging
import os
import sys
import time
from typing import List, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, HttpUrl

# ── Bootstrap ──────────────────────────────────────────────────────────────
load_dotenv()

# Ensure the project root is on sys.path when the file is run directly
sys.path.insert(0, os.path.dirname(__file__))

from prospectkeeper.adapters.nodriver_adapter import NoDriverAdapter
from prospectkeeper.infrastructure.config import Config
from prospectkeeper.infrastructure.container import Container
from prospectkeeper.adapters.supabase_adapter import SupabaseAdapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── API key guard ──────────────────────────────────────────────────────────
_API_KEY = os.environ.get("LINKEDIN_API_KEY", "dev-key")

# ── Langfuse credentials ───────────────────────────────────────────────────
_LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
_LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY", "")
_LANGFUSE_BASE_URL = os.environ.get("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")

# Sonnet 4.6 pricing (per token)
_SONNET_INPUT_COST_PER_TOKEN = 3.0 / 1_000_000
_SONNET_OUTPUT_COST_PER_TOKEN = 15.0 / 1_000_000


def _require_api_key(x_api_key: str = Header(..., description="Service API key")) -> None:
    """Dependency: reject requests with an invalid X-API-Key header."""
    if x_api_key != _API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )


# ── App ────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="ProspectKeeper API",
    description=(
        "Unified backend for ProspectKeeper — LinkedIn scraping, email outreach, "
        "and contact management.\n\n"
        "The React frontend proxies `/api/*` to this service."
    ),
    version="2.0.0",
    contact={"name": "ProspectKeeper"},
    license_info={"name": "Private"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Dependency-Injected Container (lazy init) ─────────────────────────────
_container: Optional[Container] = None


def _get_container() -> Container:
    """Lazily initialise the DI container on first use."""
    global _container
    if _container is None:
        config = Config.from_env()
        _container = Container(config)
    return _container


# ── Request / Response schemas ─────────────────────────────────────────────

class ScrapeRequest(BaseModel):
    """Parameters for a LinkedIn profile scrape."""

    linkedin_url: HttpUrl = Field(
        ...,
        description="Full LinkedIn profile URL, e.g. `https://www.linkedin.com/in/username/`.",
        examples=["https://www.linkedin.com/in/keanuczirjak/"],
    )
    contact_name: str = Field(
        ...,
        min_length=1,
        description="Full name of the person being scraped — used for log messages and name-match verification.",
        examples=["Keanu Czirjak"],
    )
    organization: str = Field(
        default="",
        description=(
            "Organisation name to check for current employment. "
            "Leave blank to skip the `still_at_organization` check and return all profile data."
        ),
        examples=["Arm", ""],
    )
    contact_id: Optional[str] = Field(
        default=None,
        description="UUID of the contact record in Supabase. When provided, the scrape result is saved as a LinkedIn snapshot for freshness tracking.",
    )


class ExperienceEntry(BaseModel):
    title: Optional[str] = Field(None, description="Job title.")
    company: Optional[str] = Field(None, description="Employer name.")
    date_range: Optional[str] = Field(None, alias="dateRange", description="Date range string from LinkedIn, e.g. 'Sep 2024 – Present'.")
    is_current: Optional[bool] = Field(None, alias="isCurrent", description="True if the date range includes 'Present'.")
    description: Optional[str] = Field(None, description="Role description / bullet points (may be empty).")

    model_config = {"populate_by_name": True}


class EducationEntry(BaseModel):
    institution: Optional[str] = Field(None, description="School or university name.")
    degree: Optional[str] = Field(None, description="Degree / qualification string.")
    date_range: Optional[str] = Field(None, alias="dateRange", description="Attendance date range.")

    model_config = {"populate_by_name": True}


class ScrapeResponse(BaseModel):
    """
    Full structured LinkedIn profile response.

    `success=False` with a non-null `error` indicates a scraping failure.
    `blocked=True` means LinkedIn returned an auth-wall or checkpoint page.
    """

    success: bool = Field(..., description="True if the profile was scraped without error.")
    blocked: bool = Field(False, description="True if LinkedIn returned an auth-wall — cookies may be expired.")
    error: Optional[str] = Field(None, description="Error message when `success=False`.")

    # Employment check
    still_at_organization: Optional[bool] = Field(
        None,
        description="True if the contact appears to still work at `organization`. Null when `organization` was not supplied.",
    )
    employment_confidence: float = Field(
        0.0,
        description="0–1 score reflecting how conclusively the scraper determined employment status. 0.92=conclusive, 0.40=profile found but unclear, 0.15=scrape failed.",
    )
    current_title: Optional[str] = Field(None, description="Most recent job title.")
    current_organization: Optional[str] = Field(None, description="Populated with `organization` when `still_at_organization=True`.")

    # Identity
    profile_url: Optional[str] = Field(None, description="Canonical profile URL after any LinkedIn redirects.")
    name: Optional[str] = Field(None, description="Full name as shown on the profile.")
    headline: Optional[str] = Field(None, description="Profile headline / tagline.")
    location: Optional[str] = Field(None, description="Location string from the profile top card.")

    # Full history
    experience: Optional[list[ExperienceEntry]] = Field(None, description="All experience entries from the profile.")
    education: Optional[list[EducationEntry]] = Field(None, description="All education entries (fetched from the `/details/education` sub-page when available).")
    skills: Optional[list[str]] = Field(None, description="All skills (fetched from the `/details/skills` sub-page when available).")

    # Metadata
    scrape_duration_seconds: Optional[float] = Field(None, description="Wall-clock time taken for the scrape.")


# ── Langfuse stats schema ──────────────────────────────────────────────────

class GenerationSummary(BaseModel):
    name: Optional[str]
    model: Optional[str]
    input_tokens: int
    output_tokens: int
    cost_usd: float
    start_time: Optional[str]


class LangfuseStatsResponse(BaseModel):
    total_calls: int = Field(..., description="Total number of Claude API calls recorded")
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_cost_usd: float
    avg_cost_per_call: float
    recent: List[GenerationSummary] = Field(..., description="Most recent 10 generations")
    langfuse_dashboard_url: str


# ── Singleton adapters ─────────────────────────────────────────────────────
_adapter = NoDriverAdapter()

_supabase: Optional[SupabaseAdapter] = None
_supabase_url = os.environ.get("SUPABASE_URL", "")
_supabase_key = os.environ.get("SUPABASE_SERVICE_KEY", "")
if _supabase_url and _supabase_key:
    _supabase = SupabaseAdapter(_supabase_url, _supabase_key)
    logger.info("Supabase adapter initialised — LinkedIn snapshots will be saved.")
else:
    logger.warning("SUPABASE_URL or SUPABASE_SERVICE_KEY not set — snapshots will not be saved.")


# ── Snapshot helpers ────────────────────────────────────────────────────────

def _profile_hash(title: Optional[str], org: Optional[str], headline: Optional[str], skills: Optional[list]) -> str:
    """SHA-256 of normalised key fields. Stable across scrapes when nothing changed."""
    data = {
        "title": (title or "").lower().strip(),
        "org": (org or "").lower().strip(),
        "headline": (headline or "").lower().strip(),
        "skills": sorted((s or "").lower().strip() for s in (skills or [])),
    }
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def _has_meaningful_data(
    title: Optional[str],
    headline: Optional[str],
    experience: Optional[list],
    education: Optional[list],
) -> bool:
    """Return False if all key profile fields are empty — avoids storing a hash of a blank page."""
    return bool(
        (title or "").strip()
        or (headline or "").strip()
        or (experience and len(experience) > 0)
        or (education and len(education) > 0)
    )


def _build_change_summary(prev: dict, current_title: Optional[str], current_org: Optional[str], headline: Optional[str]) -> dict:
    """Return only the fields that differ between previous and current scrape."""
    summary = {}
    checks = [
        ("title", prev.get("current_title"), current_title),
        ("org",   prev.get("current_org"),   current_org),
        ("headline", prev.get("headline"),   headline),
    ]
    for key, old_val, new_val in checks:
        old = (old_val or "").strip()
        new = (new_val or "").strip()
        if old != new:
            summary[f"{key}_from"] = old_val or None
            summary[f"{key}_to"]   = new_val or None
    return summary


# ── Routes ─────────────────────────────────────────────────────────────────

@app.get(
    "/health",
    summary="Health check",
    description="Returns `{\"status\": \"ok\"}`. Use this to verify the service is up before sending scrape requests.",
    tags=["Utility"],
)
async def health() -> dict:
    return {"status": "ok"}


@app.get(
    "/langfuse-stats",
    response_model=LangfuseStatsResponse,
    summary="Claude API usage from Langfuse",
    description="Queries the Langfuse REST API and returns aggregated token/cost stats for all Claude generations.",
    tags=["Observability"],
)
async def langfuse_stats() -> LangfuseStatsResponse:
    if not _LANGFUSE_PUBLIC_KEY or not _LANGFUSE_SECRET_KEY:
        raise HTTPException(
            status_code=503,
            detail="Langfuse credentials not configured (LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY).",
        )

    auth_bytes = f"{_LANGFUSE_PUBLIC_KEY}:{_LANGFUSE_SECRET_KEY}".encode()
    auth_header = "Basic " + base64.b64encode(auth_bytes).decode()

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{_LANGFUSE_BASE_URL}/api/public/observations",
            params={"type": "GENERATION", "limit": 50},
            headers={"Authorization": auth_header},
        )

    if resp.status_code != 200:
        logger.error(f"[Langfuse] API error {resp.status_code}: {resp.text[:300]}")
        raise HTTPException(
            status_code=502,
            detail=f"Langfuse API returned {resp.status_code}.",
        )

    data = resp.json()
    observations = data.get("data", [])
    meta = data.get("meta", {})
    total_pages_items = meta.get("totalItems", len(observations))

    total_input = 0
    total_output = 0
    total_cost = 0.0
    recent: List[GenerationSummary] = []

    for obs in observations:
        usage = obs.get("usage") or {}
        inp = usage.get("input") or 0
        out = usage.get("output") or 0

        # Prefer Langfuse-calculated cost; fall back to manual pricing
        cost = obs.get("calculatedTotalCost")
        if cost is None:
            cost = inp * _SONNET_INPUT_COST_PER_TOKEN + out * _SONNET_OUTPUT_COST_PER_TOKEN

        total_input += inp
        total_output += out
        total_cost += cost

        if len(recent) < 10:
            recent.append(GenerationSummary(
                name=obs.get("name"),
                model=obs.get("model"),
                input_tokens=inp,
                output_tokens=out,
                cost_usd=round(cost, 6),
                start_time=obs.get("startTime"),
            ))

    n = len(observations)
    return LangfuseStatsResponse(
        total_calls=total_pages_items,
        total_input_tokens=total_input,
        total_output_tokens=total_output,
        total_tokens=total_input + total_output,
        total_cost_usd=round(total_cost, 6),
        avg_cost_per_call=round(total_cost / n, 6) if n > 0 else 0.0,
        recent=recent,
        langfuse_dashboard_url=f"{_LANGFUSE_BASE_URL}",
    )


@app.post(
    "/scrape",
    response_model=ScrapeResponse,
    summary="Scrape a LinkedIn profile",
    description=(
        "Launches a headless Chromium browser via **nodriver**, injects the stored "
        "LinkedIn session cookies, navigates to the requested profile URL, captures "
        "the full page HTML, and parses it with BeautifulSoup.\n\n"
        "Detail sub-pages (`/details/education`, `/details/skills`) are fetched "
        "automatically when linked from the main profile — giving the complete lists "
        "rather than the truncated 2–3 item previews.\n\n"
        "**Typical latency:** 15–30 s per request (browser startup + page loads).\n\n"
        "**Auth requirement:** A valid `li_at` session cookie must be present in "
        "`linkedincookie.json` or `LINKEDIN_COOKIES_FILE`. Without it, LinkedIn will "
        "redirect to its auth-wall and `blocked=True` will be returned."
    ),
    tags=["Scraping"],
    dependencies=[],  # auth injected via parameter below for Swagger visibility
    responses={
        200: {"description": "Profile scraped (check `success` field — even failures return 200 with details)."},
        401: {"description": "Missing or invalid X-API-Key header."},
        422: {"description": "Request body validation error."},
    },
)
async def scrape_profile(
    request: ScrapeRequest,
    x_api_key: str = Header(..., description="Service API key (set LINKEDIN_API_KEY env var)."),
) -> ScrapeResponse:
    _require_api_key(x_api_key)

    t0 = time.perf_counter()
    logger.info(f"[API] Scrape request: {request.contact_name} — {request.linkedin_url}")

    result = await _adapter.verify_employment(
        contact_name=request.contact_name,
        organization=request.organization,
        linkedin_url=str(request.linkedin_url),
    )

    elapsed = round(time.perf_counter() - t0, 2)
    logger.info(
        f"[API] Scrape complete in {elapsed}s — success={result.success} "
        f"blocked={result.blocked} still_at={result.still_at_organization}"
    )

    # Convert raw dicts from the adapter into typed Pydantic models
    experience = (
        [ExperienceEntry(**e) for e in result.experience] if result.experience else None
    )
    education = (
        [EducationEntry(**e) for e in result.education] if result.education else None
    )

    if not result.success or result.blocked:
        employment_confidence = 0.15
    elif result.still_at_organization is not None:
        employment_confidence = 0.92
    else:
        employment_confidence = 0.40
    # ── Save LinkedIn snapshot for freshness tracking ───────────────────────
    if result.success and request.contact_id and _supabase and _has_meaningful_data(
        result.current_title, result.headline, result.experience, result.education
    ):
        try:
            new_hash = _profile_hash(
                result.current_title,
                result.current_organization or request.organization,
                result.headline,
                result.skills,
            )
            prev = await _supabase.get_latest_linkedin_snapshot(request.contact_id)
            data_changed = (prev is None) or (prev["profile_hash"] != new_hash)
            change_summary = _build_change_summary(
                prev or {},
                result.current_title,
                result.current_organization or request.organization,
                result.headline,
            ) if data_changed and prev else {}

            snapshot = {
                "contact_id":    request.contact_id,
                "profile_hash":  new_hash,
                "data_changed":  data_changed,
                "headline":      result.headline,
                "current_title": result.current_title,
                "current_org":   result.current_organization or request.organization or None,
                "location":      result.location,
                "experience":    [e.model_dump(by_alias=True) for e in experience] if experience else None,
                "education":     [e.model_dump(by_alias=True) for e in education] if education else None,
                "skills":        result.skills,
                "change_summary": change_summary or None,
            }
            await _supabase.save_linkedin_snapshot(snapshot)
            logger.info(
                f"[Snapshot] Saved for contact {request.contact_id} — "
                f"changed={data_changed}"
            )
        except Exception as snap_err:
            logger.warning(f"[Snapshot] Failed to save snapshot: {snap_err}")
    elif result.success and request.contact_id and _supabase:
        logger.warning(
            f"[Snapshot] Skipped for contact {request.contact_id} — "
            f"no meaningful profile data returned (blank page or auth wall)"
        )

    return ScrapeResponse(
        success=result.success,
        blocked=result.blocked,
        error=result.error,
        still_at_organization=result.still_at_organization,
        employment_confidence=employment_confidence,
        current_title=result.current_title,
        current_organization=result.current_organization,
        profile_url=result.profile_url,
        name=result.name,
        headline=result.headline,
        location=result.location,
        experience=experience,
        education=education,
        skills=result.skills,
        scrape_duration_seconds=elapsed,
    )


# ══════════════════════════════════════════════════════════════════════════
#  EMAIL ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════


class SendOneEmailRequest(BaseModel):
    """Send an info-review email to a single contact by ID."""
    contact_id: str = Field(..., description="UUID of the contact to email.")


class SendAllEmailsRequest(BaseModel):
    """Send info-review emails to all eligible contacts."""
    status_filter: Optional[str] = Field(
        None,
        description=(
            "Only email contacts with this status. "
            "Omit or set null to email every non-opted-out contact."
        ),
        examples=["unknown", "active"],
    )
    limit: int = Field(
        50,
        ge=1,
        le=500,
        description="Max number of contacts to email in this batch.",
    )
    concurrency: int = Field(
        5,
        ge=1,
        le=20,
        description="How many emails to send in parallel.",
    )


class EmailResultItem(BaseModel):
    contact_id: str
    email: str
    success: bool
    error: Optional[str] = None


class SendOneEmailResponse(BaseModel):
    success: bool
    contact_id: str
    email: str
    error: Optional[str] = None


class SendAllEmailsResponse(BaseModel):
    total_sent: int
    total_failed: int
    results: List[EmailResultItem]


@app.post(
    "/api/email/send-one",
    response_model=SendOneEmailResponse,
    summary="Send info-review email to ONE contact",
    description=(
        "Looks up the contact by ID, sends them a confirmation email via Resend, "
        "and returns the result. The email asks the contact to verify the information "
        "we have on file for them.\n\n"
        "Uses the same `EmailSenderAdapter` (Resend) as the batch pipeline."
    ),
    tags=["Email"],
)
async def send_one_email(
    request: SendOneEmailRequest,
    x_api_key: str = Header(..., description="Service API key"),
) -> SendOneEmailResponse:
    _require_api_key(x_api_key)
    container = _get_container()

    contact = await container.repository.get_contact_by_id(request.contact_id)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact {request.contact_id} not found.",
        )
    if contact.is_opted_out():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contact has opted out — cannot send email.",
        )

    result = await container.email_sender.send_confirmation(contact)

    logger.info(
        f"[Email] send-one to {contact.email}: success={result.success}"
    )
    return SendOneEmailResponse(
        success=result.success,
        contact_id=contact.id,
        email=result.email,
        error=result.error,
    )


@app.post(
    "/api/email/send-all",
    response_model=SendAllEmailsResponse,
    summary="Send info-review emails to ALL eligible contacts",
    description=(
        "Fetches contacts from the database (optionally filtered by status), "
        "and sends each one a confirmation email with bounded concurrency.\n\n"
        "Contacts who have opted out are automatically excluded.\n\n"
        "Returns a per-contact success/failure breakdown."
    ),
    tags=["Email"],
)
async def send_all_emails(
    request: SendAllEmailsRequest,
    x_api_key: str = Header(..., description="Service API key"),
) -> SendAllEmailsResponse:
    _require_api_key(x_api_key)
    container = _get_container()

    all_contacts = await container.repository.get_all_contacts()

    # Apply optional status filter
    if request.status_filter:
        all_contacts = [
            c for c in all_contacts
            if c.status.value == request.status_filter
        ]

    # Respect limit
    batch = all_contacts[: request.limit]

    logger.info(
        f"[Email] send-all: {len(batch)} contacts "
        f"(filter={request.status_filter}, limit={request.limit})"
    )

    results: List[EmailResultItem] = []
    semaphore = asyncio.Semaphore(request.concurrency)

    async def _send(contact):
        async with semaphore:
            try:
                res = await container.email_sender.send_confirmation(contact)
                results.append(EmailResultItem(
                    contact_id=contact.id,
                    email=res.email,
                    success=res.success,
                    error=res.error,
                ))
            except Exception as e:
                results.append(EmailResultItem(
                    contact_id=contact.id,
                    email=contact.email or "",
                    success=False,
                    error=str(e),
                ))

    await asyncio.gather(*[_send(c) for c in batch])

    total_ok = sum(1 for r in results if r.success)
    total_fail = len(results) - total_ok

    logger.info(f"[Email] send-all done: {total_ok} ok, {total_fail} failed")

    return SendAllEmailsResponse(
        total_sent=total_ok,
        total_failed=total_fail,
        results=results,
    )
