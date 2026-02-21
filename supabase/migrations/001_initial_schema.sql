-- ProspectKeeper: Initial Database Schema
-- Supabase/PostgreSQL
-- Best practices: UUID PKs, timestamps with timezone, RLS-ready

-- ── Contacts ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS contacts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                TEXT NOT NULL,
    email               TEXT,
    title               TEXT,
    organization        TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'unknown'
                            CHECK (status IN ('active', 'inactive', 'unknown', 'pending_confirmation', 'opted_out')),
    needs_human_review  BOOLEAN NOT NULL DEFAULT FALSE,
    review_reason       TEXT,
    district_website    TEXT,
    linkedin_url        TEXT,
    email_hash          TEXT,          -- SHA-256 hash retained after opt-out
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for common queries
CREATE INDEX IF NOT EXISTS idx_contacts_status
    ON contacts (status);
CREATE INDEX IF NOT EXISTS idx_contacts_review
    ON contacts (needs_human_review) WHERE needs_human_review = TRUE;
CREATE INDEX IF NOT EXISTS idx_contacts_org
    ON contacts (organization);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER contacts_updated_at
    BEFORE UPDATE ON contacts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ── Verification Results (Audit Log) ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS verification_results (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id          UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    status              TEXT NOT NULL,
    low_confidence_flag BOOLEAN NOT NULL DEFAULT FALSE,
    replacement_name    TEXT,
    replacement_email   TEXT,
    replacement_title   TEXT,
    evidence_urls       TEXT[],
    notes               TEXT,
    api_cost_usd        NUMERIC(10, 6) NOT NULL DEFAULT 0,
    tokens_used         INTEGER NOT NULL DEFAULT 0,
    labor_hours_saved   NUMERIC(8, 4) NOT NULL DEFAULT 0,
    value_generated_usd NUMERIC(10, 4) NOT NULL DEFAULT 0,
    highest_tier_used   SMALLINT NOT NULL DEFAULT 0,
    verified_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vresults_contact
    ON verification_results (contact_id);
CREATE INDEX IF NOT EXISTS idx_vresults_verified_at
    ON verification_results (verified_at DESC);

-- ── Batch Receipts ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS batch_receipts (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id                    TEXT NOT NULL UNIQUE,
    contacts_processed          INTEGER NOT NULL DEFAULT 0,
    contacts_verified_active    INTEGER NOT NULL DEFAULT 0,
    contacts_marked_inactive    INTEGER NOT NULL DEFAULT 0,
    replacements_found          INTEGER NOT NULL DEFAULT 0,
    flagged_for_review          INTEGER NOT NULL DEFAULT 0,
    total_api_cost_usd          NUMERIC(10, 6) NOT NULL DEFAULT 0,
    total_tokens_used           INTEGER NOT NULL DEFAULT 0,
    total_labor_hours_saved     NUMERIC(8, 2) NOT NULL DEFAULT 0,
    total_value_generated_usd   NUMERIC(10, 2) NOT NULL DEFAULT 0,
    simulated_invoice_usd       NUMERIC(10, 2) NOT NULL DEFAULT 0,
    net_roi_percentage          NUMERIC(12, 2),
    run_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_batch_receipts_run_at
    ON batch_receipts (run_at DESC);

-- ── Row Level Security (RLS) ───────────────────────────────────────────────
-- Enable RLS on all tables (backend uses service role key which bypasses RLS)
ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE verification_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE batch_receipts ENABLE ROW LEVEL SECURITY;

-- Example policy: authenticated users can read (adapt as needed)
-- CREATE POLICY "auth users read contacts" ON contacts
--     FOR SELECT USING (auth.role() = 'authenticated');
