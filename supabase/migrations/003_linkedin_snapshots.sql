-- ProspectKeeper: LinkedIn Snapshot History
-- Stores each LinkedIn scrape result so we can detect profile staleness vs. active maintenance.
--
-- Two signals:
--   last_scraped_at  → when we last checked (recency of our data)
--   last_changed_at  → when the profile itself last changed (reliability signal)
--
-- If scraped 1 month ago and data is the same → profile stale (person may have left but not updated LinkedIn)
-- If scraped 1 month ago and data changed      → actively maintained (more reliable accuracy signal)

-- ── linkedin_snapshots ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS linkedin_snapshots (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id      UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,

    -- When this scrape happened
    scraped_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- SHA-256 of normalized (title + org + headline + sorted skills)
    -- Used to detect whether anything meaningful changed between scrapes
    profile_hash    TEXT NOT NULL,

    -- TRUE if this hash differs from the immediately prior snapshot for this contact
    data_changed    BOOLEAN NOT NULL DEFAULT TRUE,

    -- Core fields captured at scrape time (for diffing + display)
    headline        TEXT,
    current_title   TEXT,
    current_org     TEXT,
    location        TEXT,

    -- Full structured data as returned by the LinkedIn scraper
    experience      JSONB,
    education       JSONB,
    skills          TEXT[],

    -- What actually changed vs the previous snapshot (only populated when data_changed = TRUE)
    -- Shape: { "title_from": "X", "title_to": "Y", "org_from": null, "org_to": null, ... }
    -- Only includes keys where old != new
    change_summary  JSONB,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Fast lookup: latest snapshot per contact, and filtering by data_changed
CREATE INDEX IF NOT EXISTS idx_linkedin_snapshots_contact
    ON linkedin_snapshots (contact_id, scraped_at DESC);

CREATE INDEX IF NOT EXISTS idx_linkedin_snapshots_changed
    ON linkedin_snapshots (contact_id, scraped_at DESC) WHERE data_changed = TRUE;

-- ── contact_linkedin_freshness (view) ──────────────────────────────────────
-- One row per contact with two key timestamps.
-- The API layer LEFT JOINs this onto contacts to serve freshness metadata.
CREATE OR REPLACE VIEW contact_linkedin_freshness AS
SELECT
    contact_id,
    MAX(scraped_at)                                             AS last_scraped_at,
    MAX(scraped_at) FILTER (WHERE data_changed = TRUE)         AS last_changed_at,
    COUNT(*)::INT                                              AS total_scrapes,
    COUNT(*) FILTER (WHERE data_changed = TRUE)::INT           AS total_changes
FROM linkedin_snapshots
GROUP BY contact_id;

-- ── RLS ────────────────────────────────────────────────────────────────────
ALTER TABLE linkedin_snapshots ENABLE ROW LEVEL SECURITY;
