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
import logging
import os
import sys
import time
from typing import List, Optional

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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── API key guard ──────────────────────────────────────────────────────────
_API_KEY = os.environ.get("LINKEDIN_API_KEY", "dev-key")


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


# ── Singleton adapter (one browser session pool) ───────────────────────────
_adapter = NoDriverAdapter()


# ── Routes ─────────────────────────────────────────────────────────────────

@app.get(
    "/health",
    summary="Health check",
    description="Returns `{\"status\": \"ok\"}`. Use this to verify the service is up before sending scrape requests.",
    tags=["Utility"],
)
async def health() -> dict:
    return {"status": "ok"}


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

    return ScrapeResponse(
        success=result.success,
        blocked=result.blocked,
        error=result.error,
        still_at_organization=result.still_at_organization,
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
