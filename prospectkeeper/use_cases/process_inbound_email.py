"""
ProcessInboundEmail Use Case
Parses inbound email replies using Claude (cheapest model: Haiku)
and updates contact records with any corrected information.
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional, List

import anthropic
from langfuse import get_client as get_langfuse_client

from ..domain.entities.contact import Contact
from ..domain.interfaces.i_data_repository import IDataRepository

logger = logging.getLogger(__name__)

# Cheapest Claude model for parsing structured data from emails
# Note: claude-3-5-haiku-latest was deprecated 2025-02-19
HAIKU_MODEL = "claude-haiku-4-5-20251001"

EMAIL_PARSE_SYSTEM_PROMPT = """You are a data-extraction assistant.
You receive the body of an email reply from a contact who was asked to review
the information we have on file for them. Your job is to extract any UPDATED
or CORRECTED fields the contact has provided.

Respond ONLY with valid JSON in this exact schema:
{
  "name": "string or null",
  "email": "string or null",
  "title": "string or null",
  "organization": "string or null",
  "district_website": "string or null",
  "linkedin_url": "string or null",
  "notes": "string or null"
}

Rules:
- Only include a field if the contact has EXPLICITLY provided new or corrected information for it.
- Set a field to null if the contact did NOT mention that field or confirmed it is correct.
- Do NOT invent or guess values. Only extract what the contact actually wrote.
- The "notes" field is for any freeform context the contact included that doesn't fit the other fields.
- If the contact says "everything looks good" or similar, return all nulls.
- Strip signatures, greetings, and quoted reply text — focus on the actual update content."""


@dataclass
class EmailParseResult:
    """Result of parsing an inbound email reply."""
    success: bool
    updates: dict                       # Only the fields that changed
    all_parsed: dict                    # Full parsed output from Claude
    tokens_input: int = 0
    tokens_output: int = 0
    cost_usd: float = 0.0
    error: Optional[str] = None


@dataclass
class ContactUpdateResult:
    """Result of the full inbound-email processing pipeline."""
    success: bool
    contact_id: Optional[str] = None
    fields_updated: Optional[List[str]] = None
    parse_result: Optional[EmailParseResult] = None
    error: Optional[str] = None


class ProcessInboundEmailUseCase:
    """
    Orchestrates: parse reply → look up contact → diff → update DB.
    Uses Claude 3.5 Haiku (cheapest) for structured extraction.
    """

    def __init__(
        self,
        repository: IDataRepository,
        anthropic_api_key: str,
    ):
        self.repository = repository
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)

    async def execute(
        self,
        sender_email: str,
        email_body: str,
        subject: str = "",
    ) -> ContactUpdateResult:
        """
        Full pipeline:
        1. Look up the contact by sender email
        2. Parse the reply body with Claude Haiku
        3. Diff parsed fields against the existing contact
        4. Persist any changes
        """
        # ── Step 1: Find the contact ──────────────────────────────────────
        contact = await self.repository.get_contact_by_email(sender_email)
        if not contact:
            logger.warning(
                f"[InboundEmail] No contact found for sender {sender_email}"
            )
            return ContactUpdateResult(
                success=False,
                error=f"No contact found for email: {sender_email}",
            )

        # ── Step 2: Parse the email body with Claude Haiku ────────────────
        parse_result = await self._parse_email(email_body, contact)
        if not parse_result.success:
            return ContactUpdateResult(
                success=False,
                contact_id=contact.id,
                parse_result=parse_result,
                error=parse_result.error,
            )

        # ── Step 3: Diff & apply changes ──────────────────────────────────
        updates = parse_result.updates
        if not updates:
            logger.info(
                f"[InboundEmail] No updates from {sender_email} — "
                f"contact confirmed info is correct."
            )
            return ContactUpdateResult(
                success=True,
                contact_id=contact.id,
                fields_updated=[],
                parse_result=parse_result,
            )

        fields_updated = self._apply_updates(contact, updates)

        # ── Step 4: Persist ───────────────────────────────────────────────
        if fields_updated:
            contact.clear_review_flag()
            await self.repository.save_contact(contact)
            logger.info(
                f"[InboundEmail] Updated contact {contact.id} ({contact.name}): "
                f"fields changed = {fields_updated}"
            )

        return ContactUpdateResult(
            success=True,
            contact_id=contact.id,
            fields_updated=fields_updated,
            parse_result=parse_result,
        )

    # ── Private helpers ───────────────────────────────────────────────────

    async def _parse_email(
        self, email_body: str, contact: Contact
    ) -> EmailParseResult:
        """Call Claude Haiku to extract structured updates from the reply."""
        prompt = (
            f"Here is the information we currently have on file for this contact:\n"
            f"  Name: {contact.name}\n"
            f"  Email: {contact.email}\n"
            f"  Title: {contact.title}\n"
            f"  Organization: {contact.organization}\n"
            f"  District Website: {contact.district_website or 'N/A'}\n"
            f"  LinkedIn URL: {contact.linkedin_url or 'N/A'}\n\n"
            f"The contact replied with this email:\n"
            f"---\n{email_body}\n---\n\n"
            f"Extract any updated or corrected fields from their reply."
        )

        try:
            with get_langfuse_client().start_as_current_generation(
                name="parse_inbound_email",
                model=HAIKU_MODEL,
                input=prompt,
                metadata={
                    "contact_id": contact.id,
                    "contact_email": contact.email,
                },
            ) as generation:
                response = self.client.messages.create(
                    model=HAIKU_MODEL,
                    max_tokens=512,
                    system=EMAIL_PARSE_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                )

                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens
                # Haiku pricing: $0.80/M input, $4.00/M output
                cost_usd = (
                    input_tokens * 0.80 + output_tokens * 4.00
                ) / 1_000_000

                generation.update(
                    output=response.content[0].text,
                    usage={"input": input_tokens, "output": output_tokens},
                )

            content = response.content[0].text
            return self._parse_claude_response(content, input_tokens, output_tokens, cost_usd)

        except Exception as e:
            logger.error(f"[InboundEmail] Claude parse error: {e}")
            return EmailParseResult(
                success=False,
                updates={},
                all_parsed={},
                error=str(e),
            )

    def _parse_claude_response(
        self,
        content: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
    ) -> EmailParseResult:
        """Parse Claude's JSON response and extract non-null updates."""
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start == -1 or end == 0:
                raise ValueError("No JSON found in Claude response")

            parsed = json.loads(content[start:end])
            # Filter to only non-null values (= actual updates)
            updates = {k: v for k, v in parsed.items() if v is not None and k != "notes"}

            return EmailParseResult(
                success=True,
                updates=updates,
                all_parsed=parsed,
                tokens_input=input_tokens,
                tokens_output=output_tokens,
                cost_usd=cost_usd,
            )
        except Exception as e:
            logger.error(
                f"[InboundEmail] Failed to parse Claude output: {e}\n{content}"
            )
            return EmailParseResult(
                success=False,
                updates={},
                all_parsed={},
                tokens_input=input_tokens,
                tokens_output=output_tokens,
                cost_usd=cost_usd,
                error=f"Parse error: {e}",
            )

    @staticmethod
    def _apply_updates(contact: Contact, updates: dict) -> List[str]:
        """
        Compare parsed updates against the contact and apply only
        fields that are actually different. Returns list of changed field names.
        """
        FIELD_MAP = {
            "name": "name",
            "email": "email",
            "title": "title",
            "organization": "organization",
            "district_website": "district_website",
            "linkedin_url": "linkedin_url",
        }

        changed: List[str] = []
        for parsed_key, attr_name in FIELD_MAP.items():
            new_value = updates.get(parsed_key)
            if new_value is None:
                continue
            current_value = getattr(contact, attr_name, None) or ""
            if str(new_value).strip().lower() != str(current_value).strip().lower():
                if parsed_key == "email":
                    contact.update_email(new_value.strip())
                else:
                    setattr(contact, attr_name, new_value.strip())
                changed.append(attr_name)
                logger.info(
                    f"[InboundEmail] Field '{attr_name}' changed: "
                    f"'{current_value}' → '{new_value.strip()}'"
                )

        return changed
