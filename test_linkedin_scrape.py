"""
Quick smoke test for NoDriverAdapter against a real LinkedIn profile.
Run: python3 test_linkedin_scrape.py

Set LINKEDIN_COOKIES_STRING in your environment if you want authenticated access.
Without cookies the profile will be public-only (may hit auth wall).
"""

import asyncio
import logging
import sys
import os

from dotenv import load_dotenv
load_dotenv("/Users/robertvassallo/Projects/com-winner/.env")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

# Add project root to path so relative imports in the adapter work
sys.path.insert(0, os.path.dirname(__file__))

from prospectkeeper.adapters.nodriver_adapter import NoDriverAdapter


TARGET_URL = "https://www.linkedin.com/in/keanuczirjak/"
CONTACT_NAME = "Keanu Czirjak"
ORGANIZATION = ""  # leave blank — just print everything


async def main():
    adapter = NoDriverAdapter()

    print(f"\n{'='*60}")
    print(f"Target  : {TARGET_URL}")
    print(f"Contact : {CONTACT_NAME}")
    print(f"Org     : {ORGANIZATION}")
    print(f"Cookies : {'SET' if os.environ.get('LINKEDIN_COOKIES_STRING') else 'NOT SET (public only)'}")
    print(f"{'='*60}\n")

    result = await adapter.verify_employment(
        contact_name=CONTACT_NAME,
        organization=ORGANIZATION,
        linkedin_url=TARGET_URL,
    )

    print(f"\n{'='*60}")
    print("RESULT")
    print(f"{'='*60}")
    print(f"success              : {result.success}")
    print(f"blocked              : {result.blocked}")
    print(f"error                : {result.error}")
    print(f"still_at_organization: {result.still_at_organization}")
    print(f"current_title        : {result.current_title}")
    print(f"current_organization : {result.current_organization}")
    print(f"profile_url          : {result.profile_url}")
    print()
    print(f"name                 : {result.name}")
    print(f"headline             : {result.headline}")
    print(f"location             : {result.location}")
    print()

    if result.experience:
        print(f"── Experience ({len(result.experience)} entries) ─────────────────")
        for e in result.experience:
            current_marker = "  ← CURRENT" if e.get("isCurrent") else ""
            dates = e.get("dateRange") or "no date"
            print(f"  [{dates}]{current_marker}")
            print(f"    {e.get('title')} @ {e.get('company')}")
            if e.get("description"):
                desc = e["description"][:120].replace("\n", " ")
                print(f"    {desc}…")
        print()

    if result.education:
        print(f"── Education ({len(result.education)} entries) ───────────────────")
        for e in result.education:
            dates = e.get("dateRange") or "no date"
            print(f"  [{dates}]  {e.get('institution')} — {e.get('degree')}")
        print()

    if result.skills:
        print(f"── Skills ({len(result.skills)} total) ──────────────────────────")
        # Print in rows of 4
        for i in range(0, len(result.skills), 4):
            print("  " + " | ".join(result.skills[i:i+4]))
        print()

    print(f"{'='*60}\n")

    if os.path.exists("debug_linkedin.png"):
        print("Screenshot saved → debug_linkedin.png")
    if os.path.exists("debug_linkedin.html"):
        size = os.path.getsize("debug_linkedin.html")
        print(f"HTML snapshot saved → debug_linkedin.html ({size:,} bytes)")


asyncio.run(main())
