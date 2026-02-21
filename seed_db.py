import asyncio
import logging
from prospectkeeper.infrastructure.config import Config
from prospectkeeper.infrastructure.container import Container
from prospectkeeper.domain.entities.contact import Contact

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def seed_data():
    config = Config.from_env()
    container = Container(config)

    contacts = [
        Contact.create(
            name="Jane Smith",
            email="jane.smith@acme.com",
            title="VP of Operations",
            organization="Acme Corp",
            district_website="https://acme.com",
            linkedin_url=None,
        ),
        Contact.create(
            name="Bob Johnson",
            email="bob.johnson@techfirm.io",
            title="Head of Engineering",
            organization="TechFirm Inc",
            district_website="https://techfirm.io",
            linkedin_url=None,
        ),
        Contact.create(
            name="Maria Garcia",
            email="maria.garcia@globalops.co",
            title="Director of Sales",
            organization="GlobalOps",
            district_website="https://globalops.co",
            linkedin_url=None,
        ),
        Contact.create(
            name="Chen Wei",
            email="chen.wei@innovate.ai",
            title="Chief Product Officer",
            organization="Innovate AI",
            district_website="https://innovate.ai",
            linkedin_url=None,
        ),
        Contact.create(
            name="Alice Brown",
            email="alice.brown@buildco.net",
            title="Operations Manager",
            organization="BuildCo",
            district_website="https://buildco.net",
            linkedin_url=None,
        ),
    ]

    for contact in contacts:
        await container.repository.insert_contact(contact)
        logger.info(f"Inserted: {contact.name}")

    logger.info("Done seeding data.")

if __name__ == "__main__":
    asyncio.run(seed_data())
