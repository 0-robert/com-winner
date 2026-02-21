# Caveats & Suggested Solutions

A frank audit of what each tier of the verification engine actually checks — and where it falls short of the core goal: *"Is this person still in **this role** at **this organization**?"*

---

## What the tiers actually look for (summary)

| Tier | What it really checks | What it claims to check |
|------|----------------------|------------------------|
| 1a ZeroBounce | Is the email address deliverable right now? | Is the contact still active? |
| 1b BS4 scraper | Does the contact's **name string** appear anywhere in the page's flat text? | Is the person listed on the company staff page? |
| 2 CamoUFox/LinkedIn | Does the **org name string** appear anywhere on whatever LinkedIn page loads? | Is the person still employed there? |
| 3 Claude | Claude's training-data knowledge about the person | Real-time public web research |

None of the first three tiers verify role, title, or the *combination* of name + current role + this org. That is only attempted at Tier 3, where Claude infers from stale training data.

---

## Tier 1a — ZeroBounce Email Validation

### Caveat 1: A deliverable email ≠ an active employee
A person can leave a company while their email address continues to accept mail. IT teams are slow to deprovision accounts — especially at mid-size companies. ZeroBounce returns `VALID` and the system escalates to scraping, which may then find the name on a cached or outdated staff page. Result: a departed employee is incorrectly confirmed as ACTIVE.

**Suggested solution:** Treat a VALID email as a *necessary but not sufficient* condition. Never return ACTIVE from email alone — only use it as a blocker for definitively bad addresses (INVALID, SPAMTRAP, etc.), which the code already does correctly. No code change needed here, just awareness.

---

### Caveat 2: Catch-all domains render Tier 1a useless for many B2B contacts
Many organisations configure their mail server to accept email to *any* address at the domain. ZeroBounce returns `CATCH_ALL` for these. The code correctly passes these through to Tier 1b, but it means a significant portion of your contact list will always skip email validation entirely and cost you a credit for no signal.

**Suggested solution:** Before calling ZeroBounce, check if the domain is already known to be catch-all (cache domain-level results across contacts). One credit spent per domain instead of per contact for catch-all domains.

---

## Tier 1b — BS4 Website Scraper

### Caveat 3 (critical): Name-in-page is not the same as currently-employed-in-role
`_parse_staff_page` does:
```python
if name_lower not in text:
    return person_found=False
```
This means **any** occurrence of the name anywhere in the flat text of the page counts as "person found". The name could appear in:
- A news article ("Alice Johnson was promoted last quarter")
- A past-employee alumni section
- A footer credit or legal disclaimer
- An event sponsor list
- A cookie consent banner that dynamically injected text

A person who left six months ago but is still mentioned in a blog post on the `/about-us` page will be returned as ACTIVE.

**Suggested solution:** Check whether the name appears in a structural context that indicates a current staff listing — specifically inside `<li>`, `<tr>`, `<article>`, or `<div>` elements that also contain a title keyword within the same element, not just within 300 characters of raw text. Use BS4's tree traversal rather than flat text substring matching.

---

### Caveat 4 (critical): JavaScript-rendered staff pages return empty HTML
`httpx` fetches static HTML only. The majority of modern company websites (React, Vue, Next.js, Webflow, etc.) render their staff pages entirely in JavaScript. BS4 will receive the shell `<div id="root"></div>` and see zero names, causing it to return `person_found=False` — correctly indicating failure, but silently escalating every modern-website contact to Tier 2/3 without any signal.

**Suggested solution:** If `_guess_staff_url` returns a URL but the parsed text is shorter than ~200 words (a sign the page didn't hydrate), log a warning and treat it as a soft skip rather than `person_found=False`. For the long term, replace `httpx` with Playwright (already a dependency if CamoUFox is installed) for Tier 1b as well, so JS pages render properly.

---

### Caveat 5: The candidate URL list is a guess for English-language companies
`_guess_staff_url` tries `/team`, `/staff`, `/our-team`, `/about/team`, `/about-us`, `/company/team`, `/people`, `/leadership` — sequentially, with a 5-second timeout each. This means up to **40 seconds of sequential HTTP requests** before it gives up. Companies in non-English markets, or that use CMSs like Drupal, Salesforce, or custom portals, will have none of these URLs. The result is always "Could not locate staff directory" and an escalation to Tier 2/3.

**Suggested solution:** Run the candidate probes concurrently with `asyncio.gather` instead of sequentially. 8 concurrent requests with 5s timeout = 5s worst case instead of 40s. Also consider adding common CMS patterns (`/about/staff`, `/who-we-are`, `/contact-us`, `/board`, `/executives`).

---

### Caveat 6: The scraper doesn't verify the page actually contains a staff directory
`_guess_staff_url` returns the **first URL that returns HTTP 200** — regardless of content. A generic `/about-us` marketing page that returns 200 but contains no staff listings will be selected, and the scraper will waste a full parse looking for names in marketing copy.

**Suggested solution:** After fetching the candidate page, check that it contains at least one occurrence of a TITLE_KEYWORD before treating it as a valid staff directory. If not, continue to the next candidate.

---

### Caveat 7: Name matching doesn't handle common real-world variations
The check is `contact_name.lower() in text`. This fails for:
- Nicknames: stored as "Robert Johnson", site lists "Bob Johnson"
- Married name changes: "Alice Smith" becomes "Alice Jones"
- Middle name inclusion/omission: "James R. Wilson" vs "James Wilson"
- Hyphenated names: stored as "Anne-Marie Dupont", site renders "Anne Marie Dupont"
- Accented characters: "José García" stored vs "Jose Garcia" on page

**Suggested solution:** Before the substring check, normalise both the stored name and the page text (strip accents, expand common nicknames, handle hyphen/space equivalence). A fuzzy match (e.g. `difflib.SequenceMatcher` ratio > 0.85) would catch most of these cases without adding dependencies.

---

## Tier 2 — CamoUFox / LinkedIn

### Caveat 8 (critical): LinkedIn org matching is `org_name in full_page_text`
`_parse_linkedin_page` does:
```python
still_there = org_lower in text_lower
```
A LinkedIn profile lists **all past and current employers**. If "Acme Corp" appears anywhere on the page — including in the "Past Experience" section — `still_there` is `True`. A person who *left* Acme Corp two years ago and is now at a different company will be reported as still employed there.

**Suggested solution:** Parse the page structure rather than the full text. On LinkedIn profiles, the "Current" experience section appears first and has distinct HTML markers. Look for the org name only within elements that precede any "Past" or date-range markers indicating a prior role. Alternatively, check if the org appears within the first 500 characters of the experience section, which is typically the current role.

---

### Caveat 9: Without a stored linkedin_url, the scraper hits LinkedIn search results — not a profile
If `contact.linkedin_url` is null, the adapter searches:
```
linkedin.com/search/results/people/?keywords={name}%20{org}
```
This lands on a **search results page**, not a profile. The org-name check runs against a list of multiple people's search result snippets. If any result on that page mentions the org name (including for other people), `still_there = True`. This is almost always True for any query involving a real company name.

**Suggested solution:** When no `linkedin_url` is stored, treat Tier 2 as skipped (return `success=False`) rather than running a search that produces unreliable signal. Save the API overhead for Tier 3 where it matters. Alternatively, implement a two-step flow: first search for the profile URL, persist it, then scrape the profile.

---

### Caveat 10: CamoUFox LinkedIn scraping violates LinkedIn's ToS
LinkedIn explicitly prohibits automated scraping in its User Agreement. Even with fingerprint evasion (CamoUFox), accounts get banned and IPs get rate-limited. For a production B2B tool this creates legal and operational risk.

**Suggested solution:** Use LinkedIn's official [Marketing Partner](https://business.linkedin.com/marketing-solutions/marketing-partners) or [Talent Solutions API](https://developer.linkedin.com/product-catalog) for employment verification — both have programmatic access with real-time data and are ToS-compliant. As a cheaper alternative, use a data enrichment provider (Clay, Apollo.io, Hunter.io) that has a LinkedIn data licence.

---

## Tier 3 — Claude AI

### Caveat 11 (critical bug): Synchronous Anthropic client called inside async context
`ClaudeAdapter.research_contact` is `async def`, but the API call is:
```python
response = self.client.messages.create(...)  # no await — sync call!
```
`self.client` is `anthropic.Anthropic()` — the **synchronous** client. Calling it directly in an async function blocks the entire asyncio event loop for the duration of every Claude API call (typically 2–15 seconds). With `BATCH_CONCURRENCY=5`, five contacts reaching Tier 3 simultaneously means 5 sequential blocking calls — the semaphore provides no actual parallelism.

**Suggested solution:** Replace `anthropic.Anthropic()` with `anthropic.AsyncAnthropic()` and `await self.client.messages.create(...)`. This is a one-line change to the constructor and a one-keyword change to the call site.

---

### Caveat 12: Claude uses training data, not live web search
The prompt says "use publicly available information only" and "determine if this person is still in their role." But Claude has no real-time web access. It answers from training data with a knowledge cutoff of ~early 2025. A contact who changed jobs in the past year will be evaluated against stale information. Claude may confidently return `contact_still_active: true` for someone who left months ago.

**Suggested solution:** Add Anthropic's `web_search` tool to the `research_contact` call. This is available in Claude 4.x and allows the model to run live Google searches before answering. It costs slightly more tokens but dramatically increases accuracy for recent job changes, which is exactly the use case.

---

### Caveat 13: Claude can hallucinate replacement email addresses
The system prompt instructs: *"Do NOT fabricate emails — only include if publicly listed."* But this is a soft constraint — Claude can and sometimes does return plausible-looking but fabricated email addresses (e.g., `firstname.lastname@company.com` constructed from the pattern). These get inserted as new Contact records in Supabase without any validation.

**Suggested solution:** Run every replacement email returned by Claude through ZeroBounce (or at minimum an MX record check) before inserting the replacement Contact. If the email is invalid, insert the replacement with an empty email field rather than a hallucinated one.

---

### Caveat 14: `confidence` field in Claude's response is never used
Claude's JSON schema includes `"confidence": "high" | "medium" | "low"`. The `_parse_response` method discards this field — it's never stored on `AIResearchResult`. Contacts with `confidence: "low"` are treated identically to `confidence: "high"`.

**Suggested solution:** Store `confidence` on `AIResearchResult` and in `VerifyContactUseCase`, route `confidence: "low"` results to `UNKNOWN + low_confidence_flag = True` rather than accepting the verdict at face value.

---

## Cross-Cutting Caveats

### Caveat 15: No role/title match at any tier
The stored `contact.title` (e.g. "VP of Engineering") is never compared against what any tier finds. A person could be confirmed "active" because their name appears on the company website — but in a completely different role. The agent would return ACTIVE and the SDR would reach out expecting a VP of Engineering but find the person is now a Sales Manager.

**Suggested solution:** In `_parse_staff_page` (Tier 1b) and `_parse_linkedin_page` (Tier 2), extract the detected title and compare it to the stored `contact.title`. If titles differ significantly, return `person_found=True` but set `low_confidence_flag=True` and include the detected title in `raw_text` for Tier 3 context. In the Claude prompt (Tier 3), explicitly include the stored title and ask Claude to flag if the person's current title differs.

---

### Caveat 16: Replacement contacts inserted without email verification
When `result.has_replacement` is True, `_apply_result` in `ProcessBatchUseCase` calls:
```python
replacement = Contact.create(name=result.replacement_name, email=result.replacement_email or "", ...)
await self.repository.insert_contact(replacement)
```
The replacement email (sourced from Claude, which may be hallucinated) goes straight into Supabase as a new Contact without any ZeroBounce check. These new contacts will enter the next batch run and potentially be contacted on bad emails.

**Suggested solution:** Run ZeroBounce on the replacement email before inserting. If INVALID, set email to `""`. This can be done inline in `_apply_result` before the `insert_contact` call.

---

### Caveat 17: No deduplication across concurrent batch runs
If two batch jobs overlap (e.g. a nightly job that runs long and a manual re-run), the same contact can be verified concurrently by two workers, producing two `verification_results` rows and potentially two conflicting `save_contact` writes (last-writer-wins on status).

**Suggested solution:** Add a `processing_lock` boolean column to `contacts` (or use Supabase's `FOR UPDATE SKIP LOCKED` on the `get_contacts_for_verification` query) so a contact being processed by one worker is skipped by another.

---

### Caveat 18: `_guess_staff_url` picks the first 200, not the best 200
The function returns the first URL candidate that responds with HTTP 200. Some sites return 200 for all routes (client-side routing SPAs) — meaning `/team` returns 200 even if the SPA renders a 404 page in the browser. The scraper would then search an empty JS shell for names and find none.

Combined with Caveat 4 (JS rendering), this means for SPA-based companies, Tier 1b silently fails for every contact, every run, burning time on 8 sequential HTTP requests that all return empty shells.

**Suggested solution:** After fetching, check that the response body contains `> N` visible text words (strip HTML first). If the content is shorter than a threshold (e.g. 100 words), treat it as a JS-rendered or empty page and move to the next candidate or skip.
