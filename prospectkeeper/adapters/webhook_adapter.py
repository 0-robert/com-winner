"""
Webhook adapter — receives inbound email replies via Zapier POST.
Run alongside Streamlit on a separate port (8502).

On receipt, delegates to ProcessInboundEmailUseCase which:
  1. Parses the reply body with Claude 3.5 Haiku (cheapest model)
  2. Diffs the parsed info against the existing contact record
  3. Updates any changed fields in Supabase
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

from ..use_cases.process_inbound_email import (
    ProcessInboundEmailUseCase,
    ContactUpdateResult,
)

logger = logging.getLogger(__name__)

app = FastAPI()

# Holds the use-case instance; set by `configure()` before server starts
_inbound_email_use_case: Optional[ProcessInboundEmailUseCase] = None


def configure(use_case: ProcessInboundEmailUseCase) -> None:
    """Inject the fully-wired use case into the webhook module."""
    global _inbound_email_use_case
    _inbound_email_use_case = use_case


def _auto_configure() -> None:
    """Auto-wire the use case from env vars (for standalone uvicorn deploys like Railway)."""
    global _inbound_email_use_case
    if _inbound_email_use_case is not None:
        return
    try:
        from dotenv import load_dotenv
        load_dotenv()
        from ..infrastructure.config import Config
        from ..infrastructure.container import Container

        config = Config.from_env()
        container = Container(config)
        _inbound_email_use_case = container.process_inbound_email_use_case
        logger.info("[Webhook] Auto-configured ProcessInboundEmailUseCase from env.")
    except Exception as e:
        logger.error(f"[Webhook] Auto-configure failed: {e}")


@app.on_event("startup")
async def on_startup():
    _auto_configure()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/webhooks/inbound-email")
async def handle_inbound_email(request: Request):
    data = await request.json()

    sender = data.get("from") or data.get("from_email") or "unknown"
    subject = data.get("subject", "No subject")
    body = data.get("body_plain") or data.get("body") or data.get("stripped-text", "")

    logger.info(f"📬 Inbound email from {sender}: {subject}")
    print(f"\n📬 NEW REPLY RECEIVED")
    print(f"   From:    {sender}")
    print(f"   Subject: {subject}")
    print(f"   Body:    {body[:200]}...")
    print(f"   Time:    {datetime.utcnow().isoformat()}\n")

    # ── Parse with Claude & update contact ────────────────────────────────
    if _inbound_email_use_case is None:
        logger.error("[Webhook] ProcessInboundEmailUseCase not configured!")
        return {
            "status": "error",
            "detail": "Email processing not configured",
            "from": sender,
        }

    result: ContactUpdateResult = await _inbound_email_use_case.execute(
        sender_email=sender,
        email_body=body,
        subject=subject,
    )

    if result.success:
        print(f"   ✅ Contact {result.contact_id} processed.")
        if result.fields_updated:
            print(f"   📝 Fields updated: {', '.join(result.fields_updated)}")
        else:
            print(f"   ℹ️  No changes — contact confirmed info is correct.")
        if result.parse_result:
            print(
                f"   💰 Haiku cost: ${result.parse_result.cost_usd:.6f} "
                f"({result.parse_result.tokens_input}+{result.parse_result.tokens_output} tokens)"
            )
    else:
        print(f"   ❌ Processing failed: {result.error}")

    return {
        "status": "processed" if result.success else "error",
        "from": sender,
        "contact_id": result.contact_id,
        "fields_updated": result.fields_updated or [],
        "error": result.error,
    }


@app.get("/health")
async def health():
    return {"status": "ok", "parser": "claude-3.5-haiku"}


def start():
    uvicorn.run(app, host="0.0.0.0", port=8502)


if __name__ == "__main__":
    start()