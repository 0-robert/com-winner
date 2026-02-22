"""
VerifyContactAgentUseCase — True agentic Claude tool_use loop.

Claude autonomously decides which tools to call and how many times,
yielding real-time SSE event dicts for streaming to the frontend.
"""

import json
import logging
from typing import AsyncGenerator

import anthropic

from ..domain.entities.contact import ContactStatus
from ..domain.interfaces.i_data_repository import IDataRepository
from ..domain.interfaces.i_email_sender_gateway import IEmailSenderGateway
from ..domain.interfaces.i_linkedin_gateway import ILinkedInGateway
from ..domain.interfaces.i_scraper_gateway import IScraperGateway

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
MAX_ITERATIONS = 10

SYSTEM_PROMPT = """You are an autonomous B2B contact verification agent for ProspectKeeper CRM.
Your job: determine if a contact is still in their current role at their organization, then update the record.

Strategy — use cheapest signals first:
1. ALWAYS start with lookup_contact to get full details including linkedin_url and district_website
2. scrape_district_website — free HTTP scrape of their org's public site, try this first
3. scrape_linkedin — headless browser verification of LinkedIn employment
4. send_confirmation_email — only if ALL other signals are ambiguous or unavailable

Decision rules:
- Two independent "not found" signals → call update_contact(status="inactive")
- One strong "confirmed active" signal (employment_confidence ≥ 0.7 or person_found=true) → call update_contact(status="active")
- Conflicting signals or insufficient data → call flag_for_review(reason="<specific reason>")

Always:
1. Start with lookup_contact
2. Explain your reasoning in one concise sentence before each tool call
3. End the session with exactly one of: update_contact OR flag_for_review"""

TOOLS = [
    {
        "name": "lookup_contact",
        "description": "Get full contact details from the database including linkedin_url and district_website.",
        "input_schema": {
            "type": "object",
            "properties": {
                "contact_id": {
                    "type": "string",
                    "description": "The contact's UUID",
                }
            },
            "required": ["contact_id"],
        },
    },
    {
        "name": "scrape_district_website",
        "description": "Scrape the contact's organization public website to check if they're still listed as staff. Free and fast — try this first.",
        "input_schema": {
            "type": "object",
            "properties": {
                "contact_name": {
                    "type": "string",
                    "description": "Full name of the contact",
                },
                "organization": {
                    "type": "string",
                    "description": "Organization name",
                },
                "district_website": {
                    "type": "string",
                    "description": "Website URL to scrape (optional — will be guessed from org name if omitted)",
                },
            },
            "required": ["contact_name", "organization"],
        },
    },
    {
        "name": "scrape_linkedin",
        "description": "Use a headless browser to scrape LinkedIn and verify current employment status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "contact_name": {
                    "type": "string",
                    "description": "Full name of the contact",
                },
                "organization": {
                    "type": "string",
                    "description": "Organization name to verify employment at",
                },
                "linkedin_url": {
                    "type": "string",
                    "description": "LinkedIn profile URL (optional but improves accuracy)",
                },
            },
            "required": ["contact_name", "organization"],
        },
    },
    {
        "name": "send_confirmation_email",
        "description": "Send a confirmation email to the contact asking them to verify their current details. Use only when other signals are inconclusive.",
        "input_schema": {
            "type": "object",
            "properties": {
                "contact_id": {
                    "type": "string",
                    "description": "The contact's UUID",
                }
            },
            "required": ["contact_id"],
        },
    },
    {
        "name": "update_contact",
        "description": "Update the contact's employment status in the database with a verified verdict.",
        "input_schema": {
            "type": "object",
            "properties": {
                "contact_id": {
                    "type": "string",
                    "description": "The contact's UUID",
                },
                "status": {
                    "type": "string",
                    "enum": ["active", "inactive"],
                    "description": "Verified employment status",
                },
                "current_title": {
                    "type": "string",
                    "description": "Updated job title if it has changed",
                },
                "current_organization": {
                    "type": "string",
                    "description": "Updated organization name if it has changed",
                },
            },
            "required": ["contact_id", "status"],
        },
    },
    {
        "name": "flag_for_review",
        "description": "Flag the contact for human review when signals are conflicting or insufficient for a confident verdict.",
        "input_schema": {
            "type": "object",
            "properties": {
                "contact_id": {
                    "type": "string",
                    "description": "The contact's UUID",
                },
                "reason": {
                    "type": "string",
                    "description": "Clear explanation of why human review is needed",
                },
            },
            "required": ["contact_id", "reason"],
        },
    },
]


class VerifyContactAgentUseCase:
    """
    True agentic Claude loop with tool_use.

    Claude decides which tools to call and iterates until it reaches a verdict.
    The execute() method is an async generator yielding SSE-compatible event dicts
    for real-time streaming to the frontend.

    Event types:
        start       — agent initialised, contact metadata
        thinking    — Claude reasoning text
        tool_call   — Claude is calling a tool (name, input)
        tool_result — tool execution result (success/error)
        final       — Claude's concluding summary
        error       — unrecoverable error
        done        — stream complete
    """

    def __init__(
        self,
        repository: IDataRepository,
        scraper: IScraperGateway,
        linkedin: ILinkedInGateway,
        email_sender: IEmailSenderGateway,
    ):
        self.repository = repository
        self.scraper = scraper
        self.linkedin = linkedin
        self.email_sender = email_sender
        self.client = anthropic.AsyncAnthropic()

    async def execute(self, contact_id: str) -> AsyncGenerator[dict, None]:
        """Run agentic tool_use loop, yielding SSE event dicts."""
        contact = await self.repository.get_contact_by_id(contact_id)
        if not contact:
            yield {"type": "error", "message": f"Contact {contact_id} not found"}
            return

        yield {
            "type": "start",
            "contact": {
                "id": contact.id,
                "name": contact.name,
                "organization": contact.organization,
                "title": contact.title,
                "status": contact.status.value,
            },
        }

        messages = [
            {
                "role": "user",
                "content": (
                    f"Verify contact: {contact.name}, currently listed as "
                    f"{contact.title} at {contact.organization} (ID: {contact_id}). "
                    f"Determine if they are still in this role and update the record."
                ),
            }
        ]

        iteration = 0
        try:
            while iteration < MAX_ITERATIONS:
                iteration += 1
                logger.info(f"[Agent] Iteration {iteration} for contact {contact_id}")

                response = await self.client.messages.create(
                    model=MODEL,
                    max_tokens=4096,
                    system=SYSTEM_PROMPT,
                    tools=TOOLS,
                    messages=messages,
                )

                # Yield any Claude reasoning text as "thinking" events
                for block in response.content:
                    if block.type == "text" and block.text.strip():
                        yield {"type": "thinking", "text": block.text.strip()}

                # Agent reached a conclusion
                if response.stop_reason == "end_turn":
                    final_text = next(
                        (b.text for b in response.content if b.type == "text"), ""
                    )
                    yield {"type": "final", "text": final_text}
                    break

                # Tool use — execute each tool and feed results back
                if response.stop_reason == "tool_use":
                    # Serialize ContentBlock objects to plain dicts for the messages array
                    messages.append(
                        {
                            "role": "assistant",
                            "content": [b.model_dump() for b in response.content],
                        }
                    )

                    tool_results = []
                    for block in response.content:
                        if block.type != "tool_use":
                            continue

                        yield {
                            "type": "tool_call",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        }

                        result = await self._execute_tool(
                            block.name, block.input, contact_id
                        )

                        yield {
                            "type": "tool_result",
                            "id": block.id,
                            "name": block.name,
                            "result": result,
                        }

                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps(result),
                            }
                        )

                    messages.append({"role": "user", "content": tool_results})

            if iteration >= MAX_ITERATIONS:
                yield {
                    "type": "error",
                    "message": f"Agent reached max iterations ({MAX_ITERATIONS}) without a verdict.",
                }

        except Exception as exc:
            logger.exception(f"[Agent] Error for contact {contact_id}: {exc}")
            yield {"type": "error", "message": str(exc)}

        yield {"type": "done"}

    async def _execute_tool(
        self, name: str, inputs: dict, default_contact_id: str
    ) -> dict:
        """Dispatch tool calls to existing adapter implementations."""

        if name == "lookup_contact":
            contact = await self.repository.get_contact_by_id(inputs["contact_id"])
            if not contact:
                return {"error": "Contact not found"}
            return {
                "id": contact.id,
                "name": contact.name,
                "email": contact.email,
                "title": contact.title,
                "organization": contact.organization,
                "status": contact.status.value,
                "linkedin_url": contact.linkedin_url,
                "district_website": contact.district_website,
                "needs_human_review": contact.needs_human_review,
            }

        if name == "scrape_district_website":
            result = await self.scraper.find_contact_on_district_site(
                contact_name=inputs["contact_name"],
                organization=inputs["organization"],
                district_website=inputs.get("district_website"),
            )
            return {
                "success": result.success,
                "person_found": result.person_found,
                "current_title": result.current_title,
                "evidence_url": result.evidence_url,
                "error": result.error,
            }

        if name == "scrape_linkedin":
            result = await self.linkedin.verify_employment(
                contact_name=inputs["contact_name"],
                organization=inputs["organization"],
                linkedin_url=inputs.get("linkedin_url"),
            )
            # Compute a confidence score from the result fields
            if not result.success or result.blocked:
                confidence = 0.15
            elif result.still_at_organization is not None:
                confidence = 0.92
            else:
                confidence = 0.40
            return {
                "success": result.success,
                "blocked": result.blocked,
                "still_at_organization": result.still_at_organization,
                "employment_confidence": confidence,
                "current_title": result.current_title,
                "current_organization": result.current_organization,
                "error": result.error,
            }

        if name == "send_confirmation_email":
            cid = inputs.get("contact_id", default_contact_id)
            contact = await self.repository.get_contact_by_id(cid)
            if not contact:
                return {"error": "Contact not found"}
            result = await self.email_sender.send_confirmation(contact)
            return {
                "success": result.success,
                "email": result.email,
                "error": result.error,
            }

        if name == "update_contact":
            cid = inputs.get("contact_id", default_contact_id)
            contact = await self.repository.get_contact_by_id(cid)
            if not contact:
                return {"error": "Contact not found"}
            status_str = inputs.get("status", "")
            if status_str == "active":
                contact.mark_active()
            elif status_str == "inactive":
                contact.mark_inactive()
            if inputs.get("current_title"):
                contact.title = inputs["current_title"]
            if inputs.get("current_organization"):
                contact.organization = inputs["current_organization"]
            await self.repository.save_contact(contact)
            return {
                "success": True,
                "contact_id": cid,
                "status": contact.status.value,
            }

        if name == "flag_for_review":
            cid = inputs.get("contact_id", default_contact_id)
            contact = await self.repository.get_contact_by_id(cid)
            if not contact:
                return {"error": "Contact not found"}
            contact.flag_for_review(inputs["reason"])
            await self.repository.save_contact(contact)
            return {
                "success": True,
                "contact_id": cid,
                "reason": inputs["reason"],
            }

        return {"error": f"Unknown tool: {name}"}
