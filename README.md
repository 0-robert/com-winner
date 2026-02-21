# ProspectKeeper

Autonomous B2B contact list maintenance agent. Verifies whether contacts are still active, flags uncertain ones for human review, and autonomously finds replacements for departed contacts — while tracking its exact economic ROI.

Built for the **Paid.ai** track at HackEurope: every batch run produces a live **Value-Proof Receipt** showing API costs vs. human SDR hours saved.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Tiered Verification Engine](#2-tiered-verification-engine)
3. [Module Map](#3-module-map)
4. [Database Schema](#4-database-schema)
5. [API Keys & Environment Setup](#5-api-keys--environment-setup)
6. [Installation](#6-installation)
7. [Running the Agent](#7-running-the-agent)
8. [Test Suite Guide](#8-test-suite-guide)
9. [The Value-Proof Receipt](#9-the-value-proof-receipt)

---

## 1. Architecture Overview

ProspectKeeper follows **Clean Architecture** (Uncle Bob) combined with **Hexagonal Architecture** (Ports & Adapters). The domain layer has zero framework dependencies — all external services are accessed through injected interfaces.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRAMEWORKS & DRIVERS                          │
│   Streamlit UI  │  CLI (main.py)  │  Supabase  │  Claude  │  httpx  │
└────────────────────────────┬────────────────────────────────────────┘
                             │  implements
┌────────────────────────────▼────────────────────────────────────────┐
│                      INTERFACE ADAPTERS                              │
│  SupabaseAdapter  BS4ScraperAdapter  ClaudeAdapter  ZeroBounce ...  │
└────────────────────────────┬────────────────────────────────────────┘
                             │  calls (via interfaces / ports)
┌────────────────────────────▼────────────────────────────────────────┐
│                         USE CASES                                    │
│   VerifyContactUseCase  │  ProcessBatchUseCase  │  CalculateROI     │
└────────────────────────────┬────────────────────────────────────────┘
                             │  operates on
┌────────────────────────────▼────────────────────────────────────────┐
│                           DOMAIN                                     │
│    Contact  │  VerificationResult  │  AgentEconomics  │  Interfaces │
└─────────────────────────────────────────────────────────────────────┘
```

### Dependency Injection

`Container` (the only place that knows about concrete implementations) wires everything together:

```mermaid
graph TD
    Config -->|credentials| Container

    Container --> SupabaseAdapter
    Container --> BS4ScraperAdapter
    Container --> ZeroBounceAdapter
    Container --> CamoUFoxAdapter
    Container --> ClaudeAdapter

    Container --> VerifyContactUseCase
    Container --> ProcessBatchUseCase
    Container --> CalculateROIUseCase

    VerifyContactUseCase -->|uses| BS4ScraperAdapter
    VerifyContactUseCase -->|uses| ZeroBounceAdapter
    VerifyContactUseCase -->|uses| CamoUFoxAdapter
    VerifyContactUseCase -->|uses| ClaudeAdapter

    ProcessBatchUseCase -->|uses| SupabaseAdapter
    ProcessBatchUseCase -->|uses| VerifyContactUseCase
    ProcessBatchUseCase -->|uses| CalculateROIUseCase
```

---

## 2. Tiered Verification Engine

The economic brain of the system. Each tier is only invoked if cheaper tiers fail to produce a confident result.

```mermaid
flowchart TD
    START([Contact to Verify]) --> T1A

    subgraph Tier1A ["Tier 1a — Email Validation (ZeroBounce, ~$0.004/call)"]
        T1A{Email valid?}
    end

    T1A -->|INVALID / SPAMTRAP / ABUSE / DO_NOT_MAIL| INACTIVE_EMAIL([INACTIVE — no escalation])
    T1A -->|VALID / CATCH_ALL / UNKNOWN| T1B

    subgraph Tier1B ["Tier 1b — Website Scraping (BS4 / httpx, free)"]
        T1B{Name found on company site?}
    end

    T1B -->|Yes| ACTIVE_SCRAPE([ACTIVE — confirmed via website])
    T1B -->|No / site missing| T2

    subgraph Tier2 ["Tier 2 — LinkedIn via CamoUFox (free, local compute)"]
        T2{Still at org on LinkedIn?}
    end

    T2 -->|Yes| ACTIVE_LI([ACTIVE — confirmed via LinkedIn])
    T2 -->|No / blocked / unavailable| T3

    subgraph Tier3 ["Tier 3 — Claude AI Deep Research (Sonnet, ~$0.003–0.02/call)"]
        T3{Claude verdict?}
    end

    T3 -->|Active| ACTIVE_AI([ACTIVE — confirmed via Claude])
    T3 -->|Inactive + replacement found| INACTIVE_REPLACE([INACTIVE — replacement inserted])
    T3 -->|Inactive, no replacement| INACTIVE_NO([INACTIVE — no replacement])
    T3 -->|Uncertain / API error| HUMAN([UNKNOWN — flagged for human review])
```

### Cost Model

| Tier | Service | Cost | When used |
|------|---------|------|-----------|
| 1a | ZeroBounce email validation | ~$0.004 / credit | Always (first check) |
| 1b | httpx + BeautifulSoup scraping | $0.00 | When email is valid/unknown |
| 2 | CamoUFox LinkedIn (headless Firefox) | $0.00 | When scraping fails |
| 3 | Claude Sonnet 4.6 via Helicone | ~$0.003–$0.025 / call | When LinkedIn fails |

---

## 3. Module Map

```
com-winner/
├── main.py                          # CLI: run / dashboard / import
│
├── prospectkeeper/
│   ├── domain/
│   │   ├── entities/
│   │   │   ├── contact.py           # Contact aggregate root + ContactStatus enum
│   │   │   ├── agent_economics.py   # AgentEconomics + ValueProofReceipt
│   │   │   └── verification_result.py  # VerificationResult value object
│   │   └── interfaces/              # Ports (ABCs) — zero external deps
│   │       ├── i_data_repository.py
│   │       ├── i_scraper_gateway.py
│   │       ├── i_linkedin_gateway.py
│   │       ├── i_ai_gateway.py
│   │       └── i_email_verification_gateway.py
│   │
│   ├── use_cases/
│   │   ├── verify_contact.py        # THE ECONOMIC BRAIN — tiered routing logic
│   │   ├── process_batch.py         # Batch orchestrator (async, semaphore-bounded)
│   │   └── calculate_roi.py         # ValueProofReceipt assembly
│   │
│   ├── adapters/                    # Concrete implementations of the ports
│   │   ├── supabase_adapter.py      # PostgreSQL via Supabase REST client
│   │   ├── bs4_scraper_adapter.py   # httpx + BeautifulSoup website scraper
│   │   ├── zerobounce_adapter.py    # ZeroBounce email verification API
│   │   ├── camofox_adapter.py       # LinkedIn via CamoUFox (optional dep)
│   │   └── claude_adapter.py        # Claude AI via Helicone proxy
│   │
│   ├── infrastructure/
│   │   ├── config.py                # Config frozen dataclass (reads from env)
│   │   └── container.py             # DI container — wires the full object graph
│   │
│   └── frontend/
│       └── app.py                   # Streamlit dashboard (4 pages)
│
├── supabase/
│   └── migrations/
│       ├── 001_initial_schema.sql   # Tables: contacts, verification_results, batch_receipts
│       └── 002_seed_data.sql        # 5 sample B2B contacts
│
├── tests/
│   ├── conftest.py                  # Shared fixtures and mock factories
│   ├── unit/
│   │   ├── domain/                  # Pure entity and value-object tests
│   │   └── use_cases/               # Use case tests with mocked gateways
│   ├── integration/
│   │   └── adapters/                # Adapter tests with mocked HTTP / SDK clients
│   └── test_infrastructure/         # Config and Container wiring tests
│
├── .env.example                     # Template — copy to .env
├── pytest.ini                       # Test runner config (asyncio_mode = auto, cov >= 80%)
├── .coveragerc                      # Coverage exclusions (frontend, camofox)
└── requirements.txt
```

### Key Data Flow (one contact verification)

```mermaid
sequenceDiagram
    participant CLI as main.py
    participant PB as ProcessBatchUseCase
    participant DB as SupabaseAdapter
    participant VC as VerifyContactUseCase
    participant ZB as ZeroBounceAdapter
    participant SC as BS4ScraperAdapter
    participant LI as CamoUFoxAdapter
    participant AI as ClaudeAdapter

    CLI->>PB: execute(ProcessBatchRequest)
    PB->>DB: get_contacts_for_verification(limit=50)
    DB-->>PB: [Contact, ...]

    loop each contact (bounded by asyncio.Semaphore)
        PB->>VC: execute(VerifyContactRequest)
        VC->>ZB: verify_email(email)
        ZB-->>VC: EmailVerificationResult

        alt email definitively invalid
            VC-->>PB: INACTIVE
        else proceed
            VC->>SC: find_contact_on_district_site(...)
            SC-->>VC: ScraperResult

            alt name found on site
                VC-->>PB: ACTIVE
            else escalate
                VC->>LI: verify_employment(...)
                LI-->>VC: LinkedInResult

                alt confirmed still at org
                    VC-->>PB: ACTIVE
                else escalate
                    VC->>AI: research_contact(...)
                    AI-->>VC: AIResearchResult
                    VC-->>PB: ACTIVE / INACTIVE / UNKNOWN
                end
            end
        end

        PB->>DB: save_contact(updated)
        PB->>DB: save_verification_result(audit)
        opt replacement found
            PB->>DB: insert_contact(replacement)
        end
    end

    PB->>PB: CalculateROIUseCase.execute(economics_list)
    PB-->>CLI: ProcessBatchResponse(receipt, results, errors)
```

---

## 4. Database Schema

Three tables in Supabase/PostgreSQL. Apply migrations via the Supabase dashboard SQL editor or CLI.

```
contacts
├── id                UUID  PK
├── name              TEXT  NOT NULL
├── email             TEXT
├── title             TEXT
├── organization      TEXT  NOT NULL
├── status            TEXT  CHECK (active|inactive|unknown|opted_out)
├── needs_human_review  BOOLEAN
├── review_reason     TEXT
├── district_website  TEXT          -- used by BS4 scraper (Tier 1b)
├── linkedin_url      TEXT          -- used by CamoUFox (Tier 2)
├── email_hash        TEXT          -- SHA-256, retained after GDPR opt-out
├── created_at        TIMESTAMPTZ
└── updated_at        TIMESTAMPTZ   -- auto-updated by trigger

verification_results              (audit log — one row per verification run)
├── id                UUID  PK
├── contact_id        UUID  FK → contacts.id
├── status            TEXT
├── low_confidence_flag  BOOLEAN
├── replacement_name  TEXT
├── replacement_email TEXT
├── replacement_title TEXT
├── evidence_urls     TEXT[]
├── notes             TEXT
├── api_cost_usd      NUMERIC
├── tokens_used       INTEGER
├── labor_hours_saved NUMERIC
├── value_generated_usd  NUMERIC
├── highest_tier_used SMALLINT      -- 1, 2, or 3
└── verified_at       TIMESTAMPTZ

batch_receipts                    (one row per batch run — the ROI receipt)
├── id                UUID  PK
├── batch_id          TEXT  UNIQUE
├── contacts_processed  INTEGER
├── contacts_verified_active  INTEGER
├── contacts_marked_inactive  INTEGER
├── replacements_found  INTEGER
├── flagged_for_review  INTEGER
├── total_api_cost_usd  NUMERIC
├── total_tokens_used   INTEGER
├── total_labor_hours_saved  NUMERIC
├── total_value_generated_usd  NUMERIC
├── simulated_invoice_usd  NUMERIC  -- outcome-based billing simulation
├── net_roi_percentage  NUMERIC
└── run_at            TIMESTAMPTZ
```

> **Apply schema**: open your Supabase project → SQL Editor → paste and run `supabase/migrations/001_initial_schema.sql`, then `002_seed_data.sql`.

---

## 5. API Keys & Environment Setup

Copy `.env.example` to `.env` and fill in each key:

```bash
cp .env.example .env
```

### Required Keys (the agent will not start without these)

| Variable | Where to get it | Notes |
|----------|----------------|-------|
| `SUPABASE_URL` | Supabase Dashboard → Project Settings → API → Project URL | `https://xxxx.supabase.co` |
| `SUPABASE_SERVICE_KEY` | Supabase Dashboard → Project Settings → API → `service_role` key | Use **service role**, not anon — it bypasses RLS for backend writes |
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys | Starts with `sk-ant-` |
| `HELICONE_API_KEY` | helicone.ai → Settings → API Keys | Starts with `sk-helicone-` — provides LLM observability and cost tracking |

### Optional Keys

| Variable | Where to get it | Effect if absent |
|----------|----------------|-----------------|
| `ZEROBOUNCE_API_KEY` | zerobounce.net → API | Tier 1a email validation is skipped; all emails treated as UNKNOWN and passed to scraper |

### Agent Tuning

| Variable | Default | Notes |
|----------|---------|-------|
| `BATCH_LIMIT` | `50` | Max contacts processed per batch run |
| `BATCH_CONCURRENCY` | `5` | Parallel verification workers (asyncio semaphore) |

### Why Helicone Is Required

Helicone acts as a transparent proxy in front of the Anthropic API, capturing token counts, costs, latency, and per-call metadata for the ROI dashboard. Claude API calls are routed through `https://anthropic.helicone.ai/v1` with your Helicone key in the headers. If you don't want Helicone, remove it from `claude_adapter.py` and drop `HELICONE_API_KEY` to optional — but you'll lose the observability dashboard.

---

## 6. Installation

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd com-winner

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy and fill in environment variables
cp .env.example .env
# edit .env with your keys (see section 5 above)

# 5. Apply database migrations
# Open Supabase Dashboard → SQL Editor and run:
#   supabase/migrations/001_initial_schema.sql
#   supabase/migrations/002_seed_data.sql
```

### Optional: LinkedIn Tier (CamoUFox)

Tier 2 (LinkedIn scraping) requires two additional installs. Commented out in `requirements.txt` intentionally — only install if you need LinkedIn verification:

```bash
pip install camoufox[geoip]
playwright install firefox
```

---

## 7. Running the Agent

### Batch verification run

```bash
python main.py run --limit 50 --concurrency 5
```

Processes up to 50 contacts from Supabase, routes each through the tiered engine, writes results back, and prints the Value-Proof Receipt.

### Import contacts from CSV

```bash
python main.py import contacts.csv
```

CSV columns: `name`, `email`, `title`, `organization`, `website` (or `district_website`), `linkedin_url`.

### Streamlit dashboard

```bash
python main.py dashboard
# or directly:
streamlit run prospectkeeper/frontend/app.py
```

Four pages:

- **All Contacts** — full contact table with status badges
- **Human Review Queue** — contacts flagged for manual attention
- **Run Agent** — trigger a batch run from the UI
- **Value-Proof Receipt** — ROI hero metric, economics table, simulated invoice

---

## 8. Test Suite Guide

363 tests, 99.66% coverage. Zero external network calls — all adapters are mocked.

```bash
# Run the full suite
pytest

# Run a specific layer
pytest tests/unit/
pytest tests/integration/
pytest tests/test_infrastructure/

# Run without coverage (faster during development)
pytest --no-cov

# Run a single file
pytest tests/unit/use_cases/test_verify_contact.py -v
```

### What Each Test File Covers

```
tests/
├── conftest.py
│   Shared fixtures: make_contact(), AsyncMock gateways,
│   sample contacts with/without district_website
│
├── unit/domain/
│   ├── test_contact.py (45 tests)
│   │   Contact.create(), flag_for_review(), update_email(),
│   │   mark_active(), mark_inactive(), opt_out() GDPR anonymisation,
│   │   ContactStatus transitions, immutability checks
│   │
│   ├── test_agent_economics.py (46 tests)
│   │   AgentEconomics: total cost, labor hours saved, ROI formula
│   │   ValueProofReceipt: aggregation, net_roi_percentage,
│   │   cost_per_contact_usd, format_receipt() string output
│   │
│   └── test_verification_result.py (12 tests)
│       has_replacement (requires name AND email),
│       needs_human_review (low_confidence OR status==UNKNOWN)
│
├── unit/use_cases/
│   ├── test_verify_contact.py (~60 tests)
│   │   All Tier 1a→1b→2→3 routing paths and short-circuit conditions,
│   │   invalid email statuses that do/don't escalate to next tier,
│   │   context_text passed through to Claude, human-review fallback
│   │
│   ├── test_calculate_roi.py (10 tests)
│   │   auto batch_id generation, receipt aggregation from list
│   │
│   └── test_process_batch.py (~30 tests)
│       contact loading, semaphore-bounded concurrency, status transitions,
│       review flagging, repo persistence calls, replacement insertion,
│       per-contact error isolation, receipt generation
│
├── integration/adapters/
│   ├── test_bs4_scraper_adapter.py (18 tests)
│   │   httpx.AsyncClient mocked via patch_async_client() helper,
│   │   staff URL discovery (404/200 side_effect sequences),
│   │   timeout on page fetch, generic exceptions,
│   │   _parse_staff_page: title keyword extraction, case-insensitive matching
│   │
│   ├── test_zerobounce_adapter.py (28 tests)
│   │   Full EmailStatus mapping parametrised (VALID/INVALID/CATCH_ALL/...),
│   │   empty email short-circuit, empty API key short-circuit,
│   │   timeout, HTTP error, _map_status direct unit tests
│   │
│   ├── test_claude_adapter.py (26 tests)
│   │   _build_prompt contents (name/title/org/context inclusion),
│   │   _parse_response (valid JSON, JSON embedded in prose,
│   │   malformed JSON, missing optional fields, tokens/cost preserved on failure),
│   │   research_contact: model name, max_tokens, token tracking,
│   │   cost formula (input*3.0 + output*15.0)/1e6, Helicone headers,
│   │   API exception → failure result with zero tokens
│   │
│   └── test_supabase_adapter.py (30+ tests)
│       _row_to_contact and _contact_to_row pure unit tests,
│       all async CRUD methods using chained_execute() mock helper:
│       get_all_contacts, get_contacts_for_verification,
│       get_contacts_needing_review, save_contact, insert_contact, bulk_update
│
└── test_infrastructure/
    ├── test_config.py (16 tests)
    │   All 4 required vars, optional vars default/override,
    │   frozen dataclass immutability, EnvironmentError naming missing vars,
    │   multi-missing listing, .env hint in error message
    │
    └── test_container.py (12 tests)
        All 8 adapter/use-case attributes present,
        object identity checks (same repository instance shared across use cases)
```

### Test Markers

```bash
pytest -m unit          # Pure unit tests — no I/O at all
pytest -m integration   # Adapter tests with mocked HTTP/SDK
pytest -m e2e           # Live credentials required (excluded by default)
```

### What Is NOT Unit Tested (and Why)

| File | Reason |
|------|--------|
| `frontend/app.py` | Streamlit requires a running server; excluded via `.coveragerc` |
| `adapters/camofox_adapter.py` | CamoUFox is an optional dependency not installed in CI; excluded via `.coveragerc` |

---

## 9. The Value-Proof Receipt

At the end of every batch run, ProspectKeeper prints (and stores in Supabase) a receipt like this:

```
======================================================================
VALUE-PROOF RECEIPT
======================================================================
Batch: 3f2a1b4c-...
Contacts Processed :  50
Active (Verified)  :  31
Inactive (Departed):  12
Replacements Found :   9
Flagged for Review :   7

--- Costs ---
Total API Cost     : $0.34
  ZeroBounce       : $0.20
  Claude (tokens)  : $0.14  (42,100 tokens)

--- Value Generated ---
Labor Hours Saved  :  4.17 hrs  (5 min/contact x 50 contacts @ $30/hr)
Replacement Value  : $22.50     ($2.50/replacement x 9 found)
Total Value        : $147.00

--- ROI ---
Net ROI            : 432%   (value - cost / cost)

--- Simulated Invoice ---
Verifications      : 50 x $0.10  = $5.00
Replacements Found :  9 x $2.50  = $22.50
TOTAL DUE          :              $27.50
======================================================================
```

**ROI constants** (defined in `agent_economics.py`):

| Constant | Value | Meaning |
|----------|-------|---------|
| `HUMAN_HOURLY_RATE_USD` | $30.00 | SDR labour cost assumed |
| `MINUTES_PER_CONTACT_VERIFICATION` | 5 min | Time a human takes per contact |
| `MINUTES_PER_REPLACEMENT_RESEARCH` | 15 min | Extra time for replacement research |
| `BILLED_RATE_PER_VERIFICATION_USD` | $0.10 | Outcome-based charge per verification |
| `BILLED_RATE_PER_REPLACEMENT_USD` | $2.50 | Outcome-based charge per replacement found |
