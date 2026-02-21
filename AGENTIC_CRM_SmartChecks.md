# Agentic CRM Smart Checks — Full Brainstorm

The goal isn't just "is this email alive?" It's: **is this person still the right person to talk to at this organisation, and do we have the best possible way to reach them?**

That reframes the problem. Email validity is one input signal out of maybe a dozen available ones. Below is an exhaustive brainstorm of every agentic method available, what it actually tells you, what it costs, and how they chain together.

---

## Mental Model: Signals vs. Verdicts

Every check below produces a **signal**, not a verdict. The agent's job is to aggregate signals into a confidence-weighted verdict:

```
CONFIRMED_ACTIVE      → high confidence, multiple signals agree, person found in role
PROBABLE_ACTIVE       → moderate confidence, email valid, name on site, no red flags
UNCERTAIN             → conflicting signals or all signals weak → flag for human review
PROBABLE_INACTIVE     → at least one strong negative signal (hard bounce, no LinkedIn)
CONFIRMED_INACTIVE    → multiple signals agree, replacement identified
OPT_OUT               → person asked to be removed
```

The agent should never rely on a single signal to flip a contact to INACTIVE — that threshold should require at least two independent negative signals.

---

## Signal Category 1: Email Signals

### 1.1 SMTP / API Validation (ZeroBounce, NeverBounce, Mailgun)
**What it tells you:** Is the mailbox technically accepting mail right now?
**What it doesn't tell you:** Whether the person is still employed.
**Cost:** ~$0.004/credit (ZeroBounce), ~$0.003 (NeverBounce), ~$0.001 (Mailgun)
**Reliability:** High for hard invalids. Low for catch-all domains (which cover ~30% of B2B companies).
**Latency:** ~1–3 seconds per call.
**Suggested function:** `verify_email_deliverability(email) → DeliverabilityResult`

### 1.2 MX Record Check (DNS lookup, free)
**What it tells you:** Does the company domain still have an active mail server?
**Why it matters:** If the company's MX records are gone, everyone at that domain is unreachable. This is a company-level signal that applies to all contacts at once.
**Cost:** $0.00 (DNS lookup via `dnspython` or `asyncio` resolver).
**Suggested function:** `check_domain_mx(domain) → DomainMailStatus`
**Agentic use:** Run once per organisation, not per contact. Cache results per domain for the batch run. If MX is dead → mark ALL contacts at that domain as `PROBABLE_INACTIVE` in one sweep.

### 1.3 Hard Bounce Ingestion from Sending Platform
**What it tells you:** An email sent as part of a real campaign bounced — the strongest possible email signal.
**Sources:** Mailgun webhooks, SendGrid Event Webhooks, Postmark bounce hooks, HubSpot sync.
**Cost:** $0.00 (passive, triggered by your own sending).
**Reliability:** Very high. Hard bounces are a near-certain signal of departure.
**Suggested function:** `ingest_bounce_webhook(payload) → void` (writes bounce flag to contact)
**Agentic use:** Treat as an automatic trigger for a full verification run on that contact.

### 1.4 Out-of-Office / Auto-Reply Parsing
**What it tells you:** A sent email received an auto-reply. These often contain:
- "I've left [Company], please contact [Name] at [email]" → instant replacement lead
- "On leave until [date]" → person is active, just unavailable
- "This email account is no longer active" → strong INACTIVE signal
**Cost:** $0.00 (parse with regex + Claude for ambiguous replies).
**Suggested function:** `parse_auto_reply(reply_text) → AutoReplyResult`
- `AutoReplyResult`: `{ is_departure: bool, forwarding_name: str, forwarding_email: str, is_temporary: bool, return_date: date }`
**Agentic use:** If `is_departure=True` and `forwarding_email` is present → auto-create replacement contact, skip Tier 3. This is one of the highest-value signals available and requires zero API cost.

### 1.5 Email Open / Click Signals (Engagement Proxy)
**What it tells you:** The contact actively engaged with a recent email → almost certainly still at the org and reachable.
**Sources:** ESP pixel tracking (Mailgun, SendGrid, HubSpot), link click webhooks.
**Cost:** $0.00 (passive signals from your own campaigns).
**Reliability:** Opens are unreliable (Apple MPP pre-fetches). Clicks are reliable.
**Suggested function:** `get_last_engagement(contact_id) → LastEngagement`
**Agentic use:** If last click was within 60 days → skip all verification tiers, set `CONFIRMED_ACTIVE`. This is free and should be the first check before spending any API credits.

### 1.6 Opt-In / Preference Centre Email
**What it tells you:** The contact explicitly confirmed or corrected their information.
**How it works:** Send a plain-text email:
> "Hi [Name], we want to make sure our records are current. Are you still [Title] at [Org]? Click one of the links below..."
> - ✅ Yes, everything's correct
> - ✏️ Update my info [magic link to a form]
> - 🚪 Remove me from this list
**Cost:** ~$0.001/email (sending cost). Requires a landing page / form backend.
**Reliability:** Very high for responses. Low response rate (~5–15%) — most people ignore.
**Suggested function:** `send_preference_email(contact) → CampaignRecord`
**Parsing function:** `handle_preference_response(token, action, updated_fields) → void`
**Agentic use:**
- Response "yes" → `CONFIRMED_ACTIVE`, reset verification clock.
- Response "update" + form data → update fields, re-verify email, `CONFIRMED_ACTIVE`.
- Response "remove" → `opt_out()`, GDPR anonymise.
- No response after 14 days → treat as weak negative signal, escalate to other tiers.
- **Important:** Only send once per quarter per contact maximum. Spam complaints destroy sender reputation.

---

## Signal Category 2: Web & Public Data Sources

### 2.1 Company Website Scraper (BS4 — current Tier 1b)
Already built. Key improvements needed (see `cav_and_s.md`):
- JS-rendered pages need Playwright
- Need structural name matching, not flat text
- Need title comparison, not just name presence

### 2.2 Google / Bing Search API
**What it tells you:** What the public internet currently says about this person + org combination.
**How:** Query `"{name}" "{organization}" site:linkedin.com OR site:{company_domain}` via Google Custom Search API or Bing Search API. Parse the result snippets for signals:
- "Director at Acme Corp" in snippet → ACTIVE signal
- "Former Director at Acme Corp" in snippet → INACTIVE signal
- Result from 3 years ago, no recent results → staleness signal
**Cost:** Google CSE: $5/1000 queries. Bing Search API: $3/1000. Both have free tiers.
**Suggested function:** `search_person_web(name, organization, domain) → SearchSignals`
**Agentic use:** Use as a soft confirmation or early red-flag before scraping. If top result says "left Acme in 2023", don't bother with company site scraping — escalate directly to Claude with the search snippet as context.

### 2.3 Google News / Bing News API
**What it tells you:** Has this person or company been mentioned in recent news?
**Patterns to detect:**
- "[Name] appointed as [Title] at [NewOrg]" → departed, has new role, possible replacement lead
- "[Org] announces layoffs" → flag ALL contacts at that org for review
- "[Org] acquired by [Acquirer]" → all contacts may need updating
- "[Name] joins [NewOrg] as [Title]" → departed signal + new org
**Cost:** Same as search APIs above.
**Suggested function:** `search_person_news(name, organization) → NewsSignals`
**Suggested function:** `search_company_news(organization, domain) → CompanyNewsSignals`
**Agentic use:** Company-level news is a force multiplier — one news event can invalidate dozens of contacts. Run this once per organisation per batch, not per contact.

### 2.4 LinkedIn (CamoUFox — current Tier 2, with fixes)
Already built. Key improvements needed:
- Must scrape the profile, not search results
- Must check "current" section only, not all past experience
- Consider official LinkedIn API alternatives

### 2.5 Twitter / X Profile
**What it tells you:** Bio often lists current role and company. Recent tweets mentioning a new employer.
**Cost:** Twitter API v2 Basic: $100/month for limited access. Free tier: very restricted.
**Suggested function:** `check_twitter_bio(handle_or_name, organization) → TwitterSignal`
**Limitations:** Many B2B contacts don't have public Twitter/X accounts. Bio is self-maintained and often stale.

### 2.6 Crunchbase / PitchBook
**What it tells you:** Executive and founder contact data for startups and funded companies. Often more current than LinkedIn for C-suite.
**Cost:** Crunchbase API: $49/month for basic access. PitchBook: enterprise pricing.
**Suggested function:** `lookup_crunchbase_person(name, organization) → CrunchbaseSignal`
**Best for:** Founder, CEO, VP contacts at VC-backed companies. Less useful for mid-market.

### 2.7 SEC EDGAR / Companies House / National Company Registers
**What it tells you:** Legally filed executive and director names. Required public filings are highly accurate.
**Sources:**
- SEC EDGAR (US public companies): free API, lists named executives in 10-K filings
- Companies House (UK): free API, lists directors
- GLEIF / OpenCorporates: multi-country company data
**Cost:** $0.00 (free government APIs).
**Suggested function:** `lookup_sec_edgar_executives(company_name, ticker) → FilingSignals`
**Best for:** CFO, CEO, board-level contacts at public companies. Extremely reliable but only covers public companies and specific jurisdictions.

### 2.8 Conference / Event Speaker Lists
**What it tells you:** Was this person listed as a speaker at a recent industry event? Speaker bios almost always include current role + org.
**Sources:** Scrape event websites (SaaStr, Dreamforce, WebSummit, industry-specific conferences). Some events publish attendee/speaker APIs.
**Cost:** $0.00 scraping (BS4/Playwright).
**Suggested function:** `search_conference_speakers(name, title_keywords) → SpeakerSignal`
**Best for:** VP+ contacts who are publicly visible at events. Confirms active role with high confidence.

### 2.9 GitHub / Open Source Activity
**What it tells you:** For technical contacts (CTO, engineers, dev rel), GitHub activity shows recent employer affiliation (company listed in profile, org membership).
**Cost:** GitHub API: free for public data, 5000 req/hr with auth.
**Suggested function:** `lookup_github_profile(name, organization) → GithubSignal`
**Best for:** Technical contacts only.

### 2.10 Company Press Releases & Investor Relations Pages
**What it tells you:** Press releases announcing new hires ("Acme Corp welcomes Jane Doe as VP of Sales") or departures. IR pages list current leadership.
**Cost:** $0.00 (scraping).
**Suggested function:** `scrape_press_releases(domain, name) → PRSignal`
**Agentic use:** Most useful as a fallback for Tier 1b — if the `/team` page fails, try `/press`, `/news`, `/investors/team`.

---

## Signal Category 3: Phone Signals

### 3.1 Phone Number Validation (Twilio Lookup, Numverify)
**What it tells you:** Is the phone number currently active? What carrier/type is it?
**Cost:** Twilio Lookup: $0.005/lookup. Numverify: $0.003/lookup.
**Reliability:** Confirms the number routes somewhere. Doesn't confirm the person still answers it.
**Suggested function:** `verify_phone(phone_number) → PhoneValidationResult`
**Limited value** for employment verification specifically. Better used as a data quality check.

### 3.2 Phone Number Portability Check
**What it tells you:** Has the phone number been ported to a different carrier? (Often a sign of switching from a company phone to personal or new employer.)
**Cost:** Twilio Lookup carrier add-on: ~$0.005.
**Marginal signal** — most people keep the same number across jobs.

---

## Signal Category 4: Data Enrichment Providers

### 4.1 Hunter.io
**What:** Email finder + verification. Given a name + company domain, finds the most likely email address format and verifies it.
**Cost:** ~$0.008/enrichment. Free tier: 25/month.
**Suggested function:** `enrich_email_hunter(name, domain) → HunterResult`
**Best use:** When you have the name + org but the stored email bounced. Hunter can find the new email format for the same org, or confirm the person has no findable email there (likely departed).

### 4.2 Apollo.io
**What:** B2B contact database with job change signals, direct dial, LinkedIn URLs.
**Cost:** $49–$99/month for API access, includes contact credits.
**Best use:** Batch enrichment. Apollo has its own job change detection — if a contact changed jobs, Apollo often knows before LinkedIn updates.
**Suggested function:** `enrich_contact_apollo(name, organization) → ApolloSignal`

### 4.3 Clearbit (now HubSpot Enrichment)
**What:** Company and person enrichment. Identifies current role, company, LinkedIn, Twitter.
**Cost:** Enterprise pricing; free tier limited.
**Suggested function:** `enrich_clearbit(email) → ClearbitSignal`
**Best use:** Email-based lookup — give Clearbit the email, get back current employer info.

### 4.4 People Data Labs
**What:** Massive dataset of person profiles aggregated from public sources. API returns current and past employment, education, social profiles.
**Cost:** $0.10–$0.15/enriched person. Has a generous free tier.
**Suggested function:** `enrich_pdl(name, email, organization) → PDLSignal`
**High quality.** Often better than Apollo for non-US contacts.

### 4.5 Lusha / RocketReach / Kaspr
**What:** Direct dial and email finders for B2B contacts. Often have fresher data than public scraping.
**Cost:** Per-credit models, roughly $0.05–$0.20/contact.
**Best use:** When the email has bounced and you want to find the person's new contact details rather than just verify the old ones.

---

## Signal Category 5: AI-Powered Deep Research

### 5.1 Claude with web_search tool (current Tier 3, but without live search)
**Improvement needed:** Add `web_search` tool to the Claude call. This allows Claude to run live Google searches, read web pages, and synthesise a verdict based on real-time information — not training data.
**Cost increase:** ~2–3x more tokens per call (search + read + synthesise). Still under $0.10/contact.
**Suggested function:** `deep_research_claude_with_search(name, org, title) → AIResearchResult`

### 5.2 Perplexity AI API
**What:** Real-time web search AI with citations. Specifically designed for factual lookups with live search.
**Cost:** ~$0.005/query (online model).
**Suggested function:** `research_perplexity(name, organization, title) → PerplexityResult`
**Best use:** Cheaper than a full Claude call for a quick factual check before committing to the full Tier 3 deep research.

### 5.3 Multi-Step Agentic Research Loop
**What:** Rather than one Claude call, an agent loop:
1. `search("Alice Johnson Acme Corp")` → get URLs
2. `fetch(url_1)` → get page text
3. `extract_employment_signals(text)` → structured signals
4. `if confidence < 0.7: search("Alice Johnson new role 2025")`
5. Repeat until confidence threshold met or max steps reached
**Cost:** 3–6 Claude calls per contact in the worst case, but most contacts resolve in 1–2.
**Suggested function:** `agentic_research_loop(contact, max_steps=5) → ResearchReport`
**This is the most powerful Tier 3 possible.** Essentially a mini research agent that keeps digging until it's confident.

### 5.4 Extraction from PDF / Document Sources
**What:** Some companies publish PDF org charts, annual reports, or board documents that list named staff with titles.
**Cost:** Claude vision or `pdfplumber` for text extraction + Claude for parsing.
**Suggested function:** `extract_contacts_from_document(url) → [ContactSignal]`
**Best use:** For regulated industries (financial services, healthcare, government) where formal org documents are published.

---

## Signal Category 6: Passive / Behavioural Signals (Zero Cost)

These are signals derived from your own system's data. They require no external API call.

### 6.1 Engagement Recency Score
The most recent interaction with the contact in your own system:
- Last email opened → `engagement_age_days`
- Last email clicked → strongest
- Last reply received → strongest
- Last form fill → strong
- Last meeting booked → strong

**Suggested function:** `compute_engagement_score(contact_id, crm_events) → EngagementScore`

If `engagement_age_days < 60` → skip all tiers, return `CONFIRMED_ACTIVE` at $0.00.
If `engagement_age_days > 365` → deprioritise the contact, add to batch queue.

### 6.2 Email Reply History
If the contact has replied to an email (any email), they are almost certainly still at the org. The reply-from header often contains their current email signature which may include updated title/phone.

**Suggested function:** `parse_reply_signature(email_body) → ContactUpdateDelta`
- Extracts name, title, phone, org from the email signature
- Compares to stored data
- Auto-updates fields where they differ

### 6.3 Domain MX Health (Organisation-Level Cache)
Run once per org domain per batch. If the domain's MX records are healthy → all contacts at that domain are "email-reachable" (though not necessarily employed). If MX is dead → flag entire org.

### 6.4 Contact Freshness / Decay Score
A contact added 3 years ago with no verification since is far more likely to be stale than one verified 2 months ago. Compute a decay score:

```
freshness_score = 1.0 - (days_since_last_verified / 365) * decay_rate
```

Where `decay_rate` reflects industry churn (typical B2B: 20–30%/year). Use this score to prioritise which contacts enter the verification queue first — highest decay gets verified first.

**Suggested function:** `compute_freshness_score(contact) → float`

---

## Agentic Orchestration: The Smart Check Pipeline

Putting it all together as a decision tree that minimises cost while maximising signal quality:

```
START: Contact enters verification queue

Step 0 — FREE PASSIVE SIGNALS (no API cost)
├── Check last engagement date
│   └── If clicked email < 60 days ago → CONFIRMED_ACTIVE, exit
├── Check for unprocessed bounce/auto-reply events
│   └── If hard bounce → trigger full verification
│   └── If auto-reply with departure info → INACTIVE + extract replacement, exit
└── Compute domain MX health (cached per org)
    └── If MX dead → PROBABLE_INACTIVE, flag org-wide

Step 1 — EMAIL SIGNAL (ZeroBounce, ~$0.004)
├── If INVALID / SPAMTRAP / ABUSE → INACTIVE
├── If CATCH_ALL / UNKNOWN → proceed with weak signal
└── If VALID → proceed with moderate positive signal

Step 2 — WEB SEARCH SNIPPET (~$0.003–$0.005)
├── Query: "{name}" "{org}" current role
├── If snippet says "former" / "left" / "ex-" → strong INACTIVE signal
│   └── If confidence high → jump to Step 5 (Claude) with context
└── If snippet confirms current role → moderate ACTIVE signal
    └── If confidence high → PROBABLE_ACTIVE, skip Steps 3–4

Step 3 — COMPANY WEBSITE SCRAPE ($0.00)
├── Try /team, /staff, /leadership, /people (concurrent, not sequential)
├── If JS-rendered → skip (Playwright optional upgrade path)
├── If name found in structural context with matching title → ACTIVE
└── If name not found → weak INACTIVE signal

Step 4 — LINKEDIN PROFILE ($0.00 if CamoUFox available)
├── Requires stored linkedin_url OR resolved from Step 2 search
├── Check CURRENT position section only (not full page)
└── If org in current section → ACTIVE
    If org in past section only → INACTIVE

Step 5 — AI DEEP RESEARCH (Claude + web_search, ~$0.01–$0.10)
├── Send all signals collected so far as context
├── Enable web_search tool for live verification
├── Claude returns: active/inactive, confidence, replacement info, evidence_urls
└── If confidence "low" → UNCERTAIN, flag for human review

Step 6 — PREFERENCE EMAIL (if UNCERTAIN and email is valid)
├── Send one-time "Is your info current?" email with magic link
├── Wait up to 14 days for response
├── Response "yes" → CONFIRMED_ACTIVE
├── Response "update" → update fields, CONFIRMED_ACTIVE
├── Response "remove" → opt_out(), GDPR anonymise
└── No response → UNCERTAIN remains, schedule next verification in 90 days

Step 7 — HUMAN REVIEW QUEUE
└── All UNCERTAIN that didn't respond to preference email
```

---

## Function Inventory (all proposed functions)

### Email Layer
```python
verify_email_deliverability(email: str) -> DeliverabilityResult
check_domain_mx(domain: str) -> DomainMailStatus
ingest_bounce_webhook(payload: dict) -> void
parse_auto_reply(reply_text: str) -> AutoReplyResult
get_last_engagement(contact_id: UUID) -> LastEngagement
send_preference_email(contact: Contact) -> CampaignRecord
handle_preference_response(token: str, action: str, updated_fields: dict) -> void
parse_reply_signature(email_body: str) -> ContactUpdateDelta
```

### Web & Public Data Layer
```python
search_person_web(name: str, organization: str, domain: str) -> SearchSignals
search_person_news(name: str, organization: str) -> NewsSignals
search_company_news(organization: str, domain: str) -> CompanyNewsSignals
scrape_company_website(domain: str, name: str) -> ScraperResult        # existing, improved
scrape_linkedin_profile(linkedin_url: str) -> LinkedInResult            # existing, improved
lookup_crunchbase_person(name: str, organization: str) -> CrunchbaseSignal
lookup_sec_edgar_executives(company_name: str, ticker: str) -> FilingSignals
search_conference_speakers(name: str, title_keywords: list) -> SpeakerSignal
lookup_github_profile(name: str, organization: str) -> GithubSignal
scrape_press_releases(domain: str, name: str) -> PRSignal
extract_contacts_from_document(url: str) -> list[ContactSignal]
```

### Enrichment Layer
```python
enrich_email_hunter(name: str, domain: str) -> HunterResult
enrich_contact_apollo(name: str, organization: str) -> ApolloSignal
enrich_pdl(name: str, email: str, organization: str) -> PDLSignal
enrich_clearbit(email: str) -> ClearbitSignal
```

### AI Research Layer
```python
deep_research_claude_with_search(name: str, org: str, title: str) -> AIResearchResult
research_perplexity(name: str, organization: str, title: str) -> PerplexityResult
agentic_research_loop(contact: Contact, max_steps: int = 5) -> ResearchReport
```

### Passive / Scoring Layer
```python
compute_engagement_score(contact_id: UUID, crm_events: list) -> EngagementScore
compute_freshness_score(contact: Contact) -> float
compute_domain_mx_health(domain: str) -> DomainMailStatus   # cached per domain per run
aggregate_signals(signals: list[Signal]) -> ConfidenceVerdict
```

### Orchestration Layer
```python
run_smart_check(contact: Contact, policy: CheckPolicy) -> VerificationResult
run_batch_smart_check(contacts: list[Contact], policy: CheckPolicy) -> BatchResult
prioritise_verification_queue(contacts: list[Contact]) -> list[Contact]   # by decay score
```

---

## Signal Reliability & Cost Matrix

| Signal Source | Cost/Contact | Speed | Reliability | Employment-Specific? | Legal Risk |
|---|---|---|---|---|---|
| Recent engagement (click) | $0.00 | Instant | Very High | Yes (indirect) | None |
| Auto-reply parsing | $0.00 | Instant | Very High | Yes | None |
| Domain MX check | $0.00 | <1s | High (domain level) | Partial | None |
| Hard bounce ingest | $0.00 | Instant | Very High | Yes | None |
| Email deliverability (ZB) | $0.004 | 1–3s | High (catch-all problem) | No | None |
| Reply signature parse | $0.00 | Instant | High (if reply exists) | Yes | None |
| Web search snippet | $0.003 | 1–2s | Medium | Partial | None |
| Company website scrape | $0.00 | 2–10s | Medium (JS problem) | Yes | Low (robots.txt) |
| News search | $0.003 | 1–2s | High for events | Yes | None |
| People Data Labs | $0.10 | <1s | High | Yes | None |
| SEC EDGAR filing | $0.00 | 1–2s | Very High | Yes (exec only) | None |
| LinkedIn scrape (CamoUFox) | $0.00 | 5–15s | High | Yes | High (ToS) |
| LinkedIn API (official) | $0.05+ | <1s | Very High | Yes | None |
| Conference speakers | $0.00 | 2–10s | High | Yes | None |
| Hunter.io | $0.008 | <1s | Medium | Partial | None |
| Apollo.io | $0.02 | <1s | High | Yes | None |
| Preference email (response) | $0.001 | 1–14 days | Very High | Yes | None |
| Preference email (no resp.) | $0.001 | 14 days | Very Low | — | None |
| Perplexity AI | $0.005 | 2–5s | High | Partial | None |
| Claude + web_search | $0.02–0.10 | 5–30s | Very High | Yes | None |
| Agentic research loop | $0.05–0.25 | 30–120s | Very High | Yes | None |
| Human review | ~$2–5 (labour) | Hours–days | Perfect | Yes | None |

---

## Key Design Principles for the Agentic System

**1. Cheapest signal first, always.**
Free passive signals (engagement history, bounces, auto-replies) should be evaluated before any API call is made. A contact who clicked a link yesterday costs $0.00 to confirm as active.

**2. Company-level signals are force multipliers.**
One news article about layoffs at Acme Corp can flag 50 contacts at once. Domain MX death invalidates an entire org. Always run org-level checks once and apply results to all contacts at that org.

**3. Negative verdicts need two independent signals.**
Never flip a contact to INACTIVE on a single signal. A 404 on the website doesn't mean they left — the website might just be down. A bounced email could be a temporary server issue. Require confirmation from a second independent source.

**4. The preference email is a superpower for low-volume high-value contacts.**
For a list of 50 key accounts (Fortune 500 contacts), a personalised "is your info still correct?" email with a magic update link is more reliable than any scraping approach — and builds goodwill rather than operating in a legal grey area. Reserve it for high-value contacts you don't want to lose.

**5. Decaying freshness means the verification queue is self-managing.**
Contacts don't need to be re-verified on a fixed schedule. They should be verified when their freshness score drops below a threshold, weighted by their commercial value (high-value accounts get verified more frequently).

**6. Treat replacement discovery as the primary success metric, not just active/inactive.**
Finding a departed person is a failure mode only if you don't also find who replaced them. The agent's real value isn't confirming actives — it's generating replacement leads for inactives.
