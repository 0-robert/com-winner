# -------------------------------------
# TestLangfuse.py — Verify Langfuse integration
#
# This script tests:
#   1. Langfuse client authentication
#   2. Anthropic + Langfuse tracing via OpenTelemetry
#
# Requires these env vars in .env:
#   LANGFUSE_PUBLIC_KEY=pk-lf-...
#   LANGFUSE_SECRET_KEY=sk-lf-...
#   LANGFUSE_BASE_URL=https://cloud.langfuse.com  (or https://us.cloud.langfuse.com)
#   ANTHROPIC_API_KEY=sk-ant-...
# -------------------------------------

import os
import sys
from dotenv import load_dotenv

load_dotenv()

# ── Step 1: Check env vars ──────────────────────────────────────────────

requiredVars = ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL"]
missingVars = [v for v in requiredVars if not os.getenv(v)]

if missingVars:
    print(f"ERROR: Missing env vars: {', '.join(missingVars)}")
    print("Add them to your .env file.")
    sys.exit(1)

print(f"Langfuse URL: {os.getenv('LANGFUSE_BASE_URL')}")
print()

# ── Step 2: Test Langfuse auth ──────────────────────────────────────────

from langfuse import get_client

langfuse = get_client()

if langfuse.auth_check():
    print("[OK] Langfuse client authenticated successfully!")
else:
    print("[FAIL] Langfuse authentication failed. Check your public/secret keys and base URL.")
    sys.exit(1)
print()

# ── Step 3: Instrument Anthropic SDK with OpenTelemetry ─────────────────

from opentelemetry.instrumentation.anthropic import AnthropicInstrumentor

AnthropicInstrumentor().instrument()
print("[OK] Anthropic SDK instrumented with OpenTelemetry (Langfuse tracing active)")
print()

# ── Step 4: Make a traced Anthropic call ────────────────────────────────

anthropicKey = os.getenv("ANTHROPIC_API_KEY", "")
if not anthropicKey:
    print("[SKIP] ANTHROPIC_API_KEY not set -- skipping live API call.")
    print("       Langfuse auth works though! Add the key to test a traced call.")
    langfuse.flush()
    sys.exit(0)

import anthropic

client = anthropic.Anthropic(api_key=anthropicKey)

print("Sending a test message to Claude (claude-haiku-4-5-20251001)...")
print()

message = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=100,
    messages=[
        {
            "role": "user",
            "content": "Say 'Hello from ProspectKeeper!' and nothing else.",
        }
    ],
)

responseText = message.content[0].text
inputTokens = message.usage.input_tokens
outputTokens = message.usage.output_tokens

print(f"[OK] Claude response: {responseText}")
print(f"     Input tokens:  {inputTokens}")
print(f"     Output tokens: {outputTokens}")
print()

# Flush traces to Langfuse before exiting
langfuse.flush()
print("[OK] Traces flushed to Langfuse -- check your dashboard!")
print(f"     Dashboard: {os.getenv('LANGFUSE_BASE_URL')}")
