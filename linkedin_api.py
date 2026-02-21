"""
LinkedIn Scraper — FastAPI Service
===================================
Wraps NoDriverAdapter as an HTTP API so any service can request a full
LinkedIn profile scrape without importing the adapter directly.

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

import logging
import os
import sys
import time
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field, HttpUrl

# ── Bootstrap ──────────────────────────────────────────────────────────────
load_dotenv()

# Ensure the project root is on sys.path when the file is run directly
sys.path.insert(0, os.path.dirname(__file__))

from prospectkeeper.adapters.nodriver_adapter import NoDriverAdapter

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
    title="LinkedIn Scraper API",
    description=(
        "Headless LinkedIn profile scraper backed by **NoDriverAdapter**.\n\n"
        "Returns structured profile data: name, headline, location, full experience "
        "history, education, and skills — including data from the `/details/` sub-pages "
        "that are truncated on the main profile view.\n\n"
        "Requires a valid LinkedIn session cookie (`li_at`) either in "
        "`linkedincookie.json` (project root) or the `LINKEDIN_COOKIES_FILE` env var."
    ),
    version="1.0.0",
    contact={"name": "ProspectKeeper"},
    license_info={"name": "Private"},
)


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
