import asyncio
import os
import traceback
from dotenv import load_dotenv

from prospectkeeper.adapters.nodriver_adapter import NoDriverAdapter

async def main():
    load_dotenv()
    
    if not os.environ.get("LINKEDIN_LI_AT"):
        print("Please make sure you have added LINKEDIN_LI_AT to your .env file!")
        return
        
    adapter = NoDriverAdapter()
    print("Beginning LinkedIn Extraction with nodriver...")
    
    # Example using a common profile to test
    contact = "Bill Gates"
    org = "Bill & Melinda Gates Foundation"
    url = "https://www.linkedin.com/in/williamhgates/"
    
    print(f"Fetching: {contact} at {org}")
    print(f"URL: {url}")
    
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    try:
        result = await adapter.verify_employment(
            contact_name=contact,
            organization=org,
            linkedin_url=url
        )
        
        print("\n--- Results ---")
        print(f"Success: {result.success}")
        if result.error:
            print(f"Error: {result.error}")
        if result.blocked:
            print(f"Blocked (Auth/Captcha Wall): {result.blocked}")
        print(f"Still at {org}?: {result.still_at_organization}")
        print(f"Extracted Title: {result.current_title}")
        print(f"Profile URL: {result.profile_url}")
    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
