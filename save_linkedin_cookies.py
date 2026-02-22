"""
Opens a Chrome browser, navigates to LinkedIn login page,
waits for you to log in, then saves cookies to linkedincookie.json.
"""
import asyncio
import json
import os

import nodriver as uc


async def main():
    print("Starting browser...")
    browser = await uc.start(headless=False)
    page = await browser.get("https://www.linkedin.com/login")

    print("\n" + "="*50)
    print("Browser is open. Please log in to LinkedIn.")
    print("Waiting until you reach the LinkedIn feed...")
    print("="*50 + "\n")

    # Wait until the user reaches the feed (URL contains /feed)
    for _ in range(300):  # wait up to 5 minutes
        await asyncio.sleep(1)
        url = page.url
        if url and "/feed" in url:
            print("Login detected! Saving cookies...")
            break
    else:
        print("Timed out waiting for login.")
        browser.stop()
        return

    # Small extra wait for all cookies to settle
    await asyncio.sleep(2)

    # Fetch all cookies from the browser
    cookies_raw = await page.send(uc.cdp.network.get_cookies())
    cookies = []
    for c in cookies_raw:
        cookies.append({
            "name": c.name,
            "value": c.value,
            "domain": c.domain,
            "path": c.path,
            "secure": c.secure,
            "httpOnly": c.http_only,
        })

    out_path = os.path.join(os.path.dirname(__file__), "linkedincookie.json")
    with open(out_path, "w") as f:
        json.dump(cookies, f, indent=2)

    li_at = next((c for c in cookies if c["name"] == "li_at"), None)
    print(f"\nSaved {len(cookies)} cookies to linkedincookie.json")
    print(f"li_at present: {'YES' if li_at else 'NO — login may not have completed'}")
    browser.stop()


if __name__ == "__main__":
    asyncio.run(main())
