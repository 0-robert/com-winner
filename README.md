# ProspectKeeper

**Autonomous B2B contact list maintenance agent with outcome-based pricing.**

Verifies existing contacts, flags uncertain ones for human review, and autonomously researches replacements — while tracking its own ROI in real time.

---

## Quick Start

```bash
# 1. Install deps
pip3 install -r requirements.txt

# 2. Configure
cp .env.example .env  # fill in your keys

# 3. Apply Supabase schema
# Run supabase/migrations/001_initial_schema.sql in your Supabase SQL editor
# Optionally run 002_seed_data.sql to load sample contacts

# 4. Run a batch
python3 main.py run --limit 50

# 5. Launch dashboard
python3 main.py dashboard

# 6. Import your own CSV (columns: name, email, title, organization, website, linkedin_url)
python3 main.py import contacts.csv
```

---

## Architecture

Clean Architecture + Hexagonal (Ports & Adapters) + DDD.

```
prospectkeeper/
├── domain/           # Entities + Interfaces (zero external deps)
│   ├── entities/     # Contact, AgentEconomics, VerificationResult, ValueProofReceipt
│   └── interfaces/   # IDataRepository, IScraperGateway, ILinkedInGateway, IAIGateway, IEmailVerificationGateway
├── use_cases/        # Business logic — VerifyContact, ProcessBatch, CalculateROI
├── adapters/         # Implementations — Supabase, BS4, ZeroBounce, CamoUFox, Claude
├── infrastructure/   # Config + DI Container
└── frontend/         # Streamlit dashboard
supabase/migrations/  # PostgreSQL schema
```

## Tiered Cost-Aware Routing

| Tier | Tool | Cost |
|------|------|------|
| 1a | ZeroBounce email validation | ~$0.004/contact |
| 1b | BS4 public website scraping | $0.00 |
| 2  | CamoUFox LinkedIn (headless) | $0.00 |
| 3  | Claude via Helicone (AI research) | ~$0.01–$0.05 |

Escalates only when cheaper tiers fail. All LLM calls traced in Helicone for cost-per-contact observability.

## Dashboard Views

- **All Contacts** — filterable table with status indicators
- **Human Review Queue** — contacts the agent couldn't resolve
- **Run Agent** — trigger a batch job with configurable size/concurrency
- **Value-Proof Receipt** — live ROI receipt + simulated outcome-based invoice

## Environment Variables

See `.env.example` for all required variables.
