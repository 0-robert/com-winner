"""
Webhook adapter — receives inbound email replies via Zapier POST.
Run alongside Streamlit on a separate port (8502).
"""

import logging
from datetime import datetime
from fastapi import FastAPI, Request
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

app = FastAPI()


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

    # TODO: save to Supabase, trigger verification logic, etc.

    return {"status": "received", "from": sender}


@app.get("/health")
async def health():
    return {"status": "ok"}


def start():
    uvicorn.run(app, host="0.0.0.0", port=8502)


if __name__ == "__main__":
    start()