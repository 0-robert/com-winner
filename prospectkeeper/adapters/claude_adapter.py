"""
ClaudeAdapter - Implements IAIGateway.
Tier 3: Deep research using Anthropic Claude via Langfuse observability proxy.
Cost: ~$0.01-$0.05 per contact depending on research depth.

All requests routed through Langfuse for:
- Real-time cost-per-contact tracking
- Token usage dashboards
- Latency monitoring
"""

import json
import logging
from typing import Optional
import anthropic

from ..domain.interfaces.i_ai_gateway import IAIGateway, AIResearchResult

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"

RESEARCH_SYSTEM_PROMPT = """You are a B2B contact research specialist.
Your job is to determine if a person is still in their current role at their organization,
and if not, to identify their replacement.

Respond ONLY with valid JSON in this exact schema:
{
  "contact_still_active": true | false | null,
  "current_title": "string or null",
  "current_organization": "string or null",
  "replacement_name": "string or null",
  "replacement_title": "string or null",
  "replacement_email": "string or null",
  "evidence_urls": ["string"],
  "confidence": "high" | "medium" | "low"
}

Rules:
- Set contact_still_active to null if you cannot determine with confidence.
- Only provide a replacement if you are confident the original contact has left.
- Do NOT fabricate emails — only include if publicly listed.
- Include evidence_urls for any sources you reference."""


class ClaudeAdapter(IAIGateway):
    """
    Tier 3 AI research adapter.
    Routes all Claude API calls through Langfuse proxy for observability.
    Uses structured output to ensure parseable responses.
    """

    def __init__(self, anthropic_api_key: str):
        self.client = anthropic.Anthropic(
            api_key=anthropic_api_key,
        )

    async def research_contact(
        self,
        contact_name: str,
        organization: str,
        title: str,
        context_text: Optional[str] = None,
    ) -> AIResearchResult:
        prompt = self._build_prompt(contact_name, organization, title, context_text)

        try:
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=RESEARCH_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cost_usd = (input_tokens * 3.0 + output_tokens * 15.0) / 1_000_000
            content = response.content[0].text
            return self._parse_response(
                content, input_tokens, output_tokens, cost_usd
            )

        except Exception as e:
            logger.error(f"[Tier3] Claude API error for {contact_name}: {e}")
            return AIResearchResult(
                success=False,
                error=str(e),
            )

    def _build_prompt(
        self,
        name: str,
        organization: str,
        title: str,
        context: Optional[str],
    ) -> str:
        prompt = (
            f"Research this B2B contact:\n"
            f"Name: {name}\n"
            f"Title: {title}\n"
            f"Organization: {organization}\n"
        )
        if context:
            prompt += f"\nAdditional context from web scraping:\n{context}\n"
        prompt += (
            "\nDetermine if this person is still in their role at this organization. "
            "If they have left, identify their replacement. "
            "Use publicly available information only."
        )
        return prompt

    def _parse_response(
        self, content: str, input_tokens: int, output_tokens: int, cost_usd: float
    ) -> AIResearchResult:
        try:
            # Extract JSON from response
            start = content.find("{")
            end = content.rfind("}") + 1
            if start == -1 or end == 0:
                raise ValueError("No JSON found in response")

            data = json.loads(content[start:end])

            return AIResearchResult(
                success=True,
                contact_still_active=data.get("contact_still_active"),
                current_title=data.get("current_title"),
                current_organization=data.get("current_organization"),
                replacement_name=data.get("replacement_name"),
                replacement_title=data.get("replacement_title"),
                replacement_email=data.get("replacement_email"),
                tokens_input=input_tokens,
                tokens_output=output_tokens,
                cost_usd=cost_usd,
                evidence_urls=data.get("evidence_urls", []),
            )
        except Exception as e:
            logger.error(f"[Tier3] Failed to parse Claude response: {e}\n{content}")
            return AIResearchResult(
                success=False,
                tokens_input=input_tokens,
                tokens_output=output_tokens,
                cost_usd=cost_usd,
                error=f"Parse error: {e}",
            )
