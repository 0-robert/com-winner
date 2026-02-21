import asyncio
import logging
from prospectkeeper.adapters.nodriver_adapter import NoDriverAdapter

logging.basicConfig(level=logging.DEBUG)

async def main():
    adapter = NoDriverAdapter()
    result = await adapter.verify_employment(
        contact_name="Keanu Czirjak",
        organization="Arm",
        linkedin_url="https://www.linkedin.com/in/keanuczirjak/"
    )
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
