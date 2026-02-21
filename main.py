"""
ProspectKeeper — CLI Entry Point

Usage:
  # Run a batch verification job
  python main.py run --limit 50

  # Launch the Streamlit dashboard
  python main.py dashboard

  # Import contacts from a CSV
  python main.py import contacts.csv
"""

import asyncio
import csv
import sys
import argparse
import logging
from dotenv import load_dotenv
load_dotenv()
import threading
from prospectkeeper.adapters.webhook_adapter import start as start_webhook, configure as configure_webhook



logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("prospectkeeper")

from langfuse import get_client as get_langfuse_client


def parse_args():
    parser = argparse.ArgumentParser(
        description="ProspectKeeper — Autonomous B2B Contact Maintenance Agent"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run command
    run_parser = subparsers.add_parser("run", help="Run a batch verification job")
    run_parser.add_argument(
        "--limit", type=int, default=50, help="Max contacts to process (default: 50)"
    )
    run_parser.add_argument(
        "--concurrency", type=int, default=5, help="Parallel workers (default: 5)"
    )
    run_parser.add_argument(
        "--tier", type=str, choices=["free", "paid"], default="free", help="Verification tier (default: free)"
    )

    # dashboard command
    subparsers.add_parser("dashboard", help="Launch the Streamlit dashboard")

    # import command
    import_parser = subparsers.add_parser(
        "import", help="Import contacts from a CSV file"
    )
    import_parser.add_argument("file", help="Path to CSV file")

    return parser.parse_args()


async def run_batch(limit: int, concurrency: int, tier: str):
    from prospectkeeper.infrastructure.config import Config
    from prospectkeeper.infrastructure.container import Container
    from prospectkeeper.use_cases.process_batch import ProcessBatchRequest

    config = Config.from_env()
    container = Container(config)

    logger.info(f"Starting batch run: tier={tier}, limit={limit}, concurrency={concurrency}")
    response = await container.process_batch_use_case.execute(
        ProcessBatchRequest(tier=tier, limit=limit, concurrency=concurrency)
    )

    print("\n" + "=" * 70)
    print("VALUE-PROOF RECEIPT")
    print("=" * 70)
    print(response.receipt.format_receipt())
    print("=" * 70)

    if response.errors:
        print(f"\n⚠ {len(response.errors)} error(s) during batch:")
        for err in response.errors:
            print(f"  • {err}")

    # Flush OTel spans to Langfuse before process exits
    get_langfuse_client().flush()


async def import_csv(filepath: str):
    from prospectkeeper.infrastructure.config import Config
    from prospectkeeper.infrastructure.container import Container
    from prospectkeeper.domain.entities.contact import Contact

    config = Config.from_env()
    container = Container(config)

    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            contact = Contact.create(
                name=row.get("name", ""),
                email=row.get("email", ""),
                title=row.get("title", ""),
                organization=row.get("organization", ""),
                district_website=row.get("website") or row.get("district_website"),
                linkedin_url=row.get("linkedin_url"),
            )
            await container.repository.insert_contact(contact)
            count += 1
            logger.info(f"Imported: {contact.name} @ {contact.organization}")

    logger.info(f"Import complete: {count} contacts added.")


def launch_dashboard():
    import subprocess
    dashboard_path = "prospectkeeper/frontend/app.py"
    logger.info(f"Launching Streamlit dashboard at {dashboard_path}")
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", dashboard_path],
        check=True,
    )


def main():
    args = parse_args()

    # Wire the inbound-email use case into the webhook before starting it
    from prospectkeeper.infrastructure.config import Config
    from prospectkeeper.infrastructure.container import Container

    config = Config.from_env()
    container = Container(config)
    configure_webhook(container.process_inbound_email_use_case)

    webhook_thread = threading.Thread(target=start_webhook, daemon=True)
    webhook_thread.start()

    if args.command == "run":
        asyncio.run(run_batch(args.limit, args.concurrency, args.tier))

    elif args.command == "dashboard":
        launch_dashboard()

    elif args.command == "import":
        asyncio.run(import_csv(args.file))


if __name__ == "__main__":
    main()
