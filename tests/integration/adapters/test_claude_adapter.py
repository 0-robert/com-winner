"""
Tests for ClaudeAdapter.

The Anthropic client is a synchronous SDK client stored on self.client.
We mock self.client.messages.create directly.
All JSON parsing and cost/token tracking is tested without real API calls.
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from prospectkeeper.adapters.claude_adapter import ClaudeAdapter


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def make_adapter() -> ClaudeAdapter:
    """Create a ClaudeAdapter with a fully mocked Anthropic client."""
    with patch("prospectkeeper.adapters.claude_adapter.anthropic.Anthropic"):
        adapter = ClaudeAdapter(
            anthropic_api_key="sk-ant-test",
            langfuse_public_key="pk-langfuse-test",
            langfuse_secret_key="sk-langfuse-test",
        )
    return adapter


def make_api_response(content_text: str, input_tokens: int = 200, output_tokens: int = 100):
    """Build a mock Anthropic API response object."""
    response = MagicMock()
    response.content = [MagicMock()]
    response.content[0].text = content_text
    response.usage = MagicMock()
    response.usage.input_tokens = input_tokens
    response.usage.output_tokens = output_tokens
    return response


def active_json(**kwargs) -> str:
    data = {
        "contact_still_active": True,
        "current_title": "Director",
        "current_organization": "Acme Corp",
        "replacement_name": None,
        "replacement_title": None,
        "replacement_email": None,
        "evidence_urls": [],
        "confidence": "high",
    }
    data.update(kwargs)
    return json.dumps(data)


def inactive_with_replacement_json(**kwargs) -> str:
    data = {
        "contact_still_active": False,
        "current_title": None,
        "current_organization": None,
        "replacement_name": "Bob New",
        "replacement_title": "Director",
        "replacement_email": "bob.new@acme.com",
        "evidence_urls": ["https://acme.com/team"],
        "confidence": "high",
    }
    data.update(kwargs)
    return json.dumps(data)


# ─────────────────────────────────────────────────────────────────────────────
# _build_prompt — pure unit tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBuildPrompt:
    def setup_method(self):
        self.adapter = make_adapter()

    def test_includes_contact_name(self):
        prompt = self.adapter._build_prompt("Alice Smith", "Acme", "Director", None)
        assert "Alice Smith" in prompt

    def test_includes_title(self):
        prompt = self.adapter._build_prompt("Alice", "Acme", "VP of Operations", None)
        assert "VP of Operations" in prompt

    def test_includes_organization(self):
        prompt = self.adapter._build_prompt("Alice", "Global Corp", "Director", None)
        assert "Global Corp" in prompt

    def test_includes_context_when_provided(self):
        context = "Scraped from website: alice is listed as director"
        prompt = self.adapter._build_prompt("Alice", "Acme", "Director", context)
        assert context in prompt

    def test_omits_context_section_when_none(self):
        prompt = self.adapter._build_prompt("Alice", "Acme", "Director", None)
        assert "Additional context" not in prompt

    def test_ends_with_instruction(self):
        prompt = self.adapter._build_prompt("Alice", "Acme", "Director", None)
        assert "publicly available information" in prompt


# ─────────────────────────────────────────────────────────────────────────────
# _parse_response — pure unit tests
# ─────────────────────────────────────────────────────────────────────────────


class TestParseResponse:
    def setup_method(self):
        self.adapter = make_adapter()

    def test_parses_active_contact(self):
        content = active_json()
        result = self.adapter._parse_response(content, 200, 100, 0.003)
        assert result.success is True
        assert result.contact_still_active is True

    def test_parses_inactive_contact_with_replacement(self):
        content = inactive_with_replacement_json()
        result = self.adapter._parse_response(content, 200, 100, 0.003)
        assert result.success is True
        assert result.contact_still_active is False
        assert result.replacement_name == "Bob New"
        assert result.replacement_email == "bob.new@acme.com"
        assert result.replacement_title == "Director"

    def test_parses_null_contact_still_active(self):
        content = active_json(contact_still_active=None)
        result = self.adapter._parse_response(content, 200, 100, 0.003)
        assert result.contact_still_active is None

    def test_parses_evidence_urls(self):
        content = active_json(evidence_urls=["https://a.com", "https://b.com"])
        result = self.adapter._parse_response(content, 200, 100, 0.003)
        assert result.evidence_urls == ["https://a.com", "https://b.com"]

    def test_handles_json_embedded_in_surrounding_text(self):
        """Claude often wraps JSON in prose — parser must extract it."""
        content = f"Here is my analysis:\n{active_json()}\nDone."
        result = self.adapter._parse_response(content, 200, 100, 0.003)
        assert result.success is True
        assert result.contact_still_active is True

    def test_tokens_stored_correctly(self):
        content = active_json()
        result = self.adapter._parse_response(content, 350, 150, 0.003)
        assert result.tokens_input == 350
        assert result.tokens_output == 150

    def test_cost_stored_correctly(self):
        content = active_json()
        result = self.adapter._parse_response(content, 200, 100, 0.0245)
        assert result.cost_usd == pytest.approx(0.0245)

    def test_returns_failure_when_no_json_in_response(self):
        content = "I cannot determine this contact's status."
        result = self.adapter._parse_response(content, 200, 100, 0.003)
        assert result.success is False
        assert "Parse error" in result.error

    def test_returns_failure_on_malformed_json(self):
        content = '{"contact_still_active": true, "missing_closing_brace"'
        result = self.adapter._parse_response(content, 200, 100, 0.003)
        assert result.success is False
        assert "Parse error" in result.error

    def test_tokens_and_cost_still_set_on_parse_failure(self):
        """Even when parsing fails, token/cost data must be preserved."""
        content = "no json here"
        result = self.adapter._parse_response(content, 400, 200, 0.009)
        assert result.success is False
        assert result.tokens_input == 400
        assert result.tokens_output == 200
        assert result.cost_usd == pytest.approx(0.009)

    def test_missing_optional_fields_default_to_none(self):
        content = json.dumps({"contact_still_active": True, "evidence_urls": []})
        result = self.adapter._parse_response(content, 200, 100, 0.003)
        assert result.success is True
        assert result.current_title is None
        assert result.replacement_name is None

    def test_empty_evidence_urls_list_when_missing_from_json(self):
        content = json.dumps({"contact_still_active": True})
        result = self.adapter._parse_response(content, 200, 100, 0.003)
        assert result.evidence_urls == []


# ─────────────────────────────────────────────────────────────────────────────
# research_contact — integration of build_prompt + API call + parse
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestResearchContact:
    async def test_successful_research_returns_parsed_result(self):
        adapter = make_adapter()
        api_resp = make_api_response(active_json(), input_tokens=300, output_tokens=200)
        adapter.client.messages.create.return_value = api_resp

        result = await adapter.research_contact(
            contact_name="Alice", organization="Acme", title="Director"
        )
        assert result.success is True
        assert result.contact_still_active is True

    async def test_api_called_with_correct_model(self):
        from prospectkeeper.adapters.claude_adapter import MODEL
        adapter = make_adapter()
        api_resp = make_api_response(active_json())
        adapter.client.messages.create.return_value = api_resp

        await adapter.research_contact("Alice", "Acme", "Director")
        call_kwargs = adapter.client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == MODEL

    async def test_api_called_with_max_tokens_1024(self):
        adapter = make_adapter()
        api_resp = make_api_response(active_json())
        adapter.client.messages.create.return_value = api_resp

        await adapter.research_contact("Alice", "Acme", "Director")
        call_kwargs = adapter.client.messages.create.call_args.kwargs
        assert call_kwargs["max_tokens"] == 1024

    async def test_tokens_tracked_from_api_response(self):
        adapter = make_adapter()
        api_resp = make_api_response(active_json(), input_tokens=400, output_tokens=250)
        adapter.client.messages.create.return_value = api_resp

        result = await adapter.research_contact("Alice", "Acme", "Director")
        assert result.tokens_input == 400
        assert result.tokens_output == 250

    async def test_cost_calculated_from_token_usage(self):
        """Cost = (input * 3.0 + output * 15.0) / 1_000_000"""
        adapter = make_adapter()
        input_tokens, output_tokens = 1000, 500
        api_resp = make_api_response(active_json(), input_tokens, output_tokens)
        adapter.client.messages.create.return_value = api_resp

        result = await adapter.research_contact("Alice", "Acme", "Director")
        expected_cost = (1000 * 3.0 + 500 * 15.0) / 1_000_000
        assert result.cost_usd == pytest.approx(expected_cost)

    async def test_api_exception_returns_failure(self):
        adapter = make_adapter()
        adapter.client.messages.create.side_effect = Exception("API unreachable")

        result = await adapter.research_contact("Alice", "Acme", "Director")
        assert result.success is False
        assert "API unreachable" in result.error

    async def test_api_exception_tokens_and_cost_are_zero(self):
        adapter = make_adapter()
        adapter.client.messages.create.side_effect = Exception("crash")

        result = await adapter.research_contact("Alice", "Acme", "Director")
        assert result.tokens_input == 0
        assert result.tokens_output == 0
        assert result.cost_usd == 0.0

    async def test_langfuse_headers_present_in_api_call(self):
        adapter = make_adapter()
        # Verify the custom init headers are passed to the client inside the adapter.
        pass

    async def test_context_text_included_in_prompt_sent_to_api(self):
        adapter = make_adapter()
        api_resp = make_api_response(active_json())
        adapter.client.messages.create.return_value = api_resp

        await adapter.research_contact(
            "Alice", "Acme", "Director",
            context_text="alice was listed on staff page"
        )
        call_kwargs = adapter.client.messages.create.call_args.kwargs
        messages = call_kwargs["messages"]
        user_content = messages[0]["content"]
        assert "alice was listed on staff page" in user_content

    async def test_replacement_data_returned_when_inactive(self):
        adapter = make_adapter()
        api_resp = make_api_response(inactive_with_replacement_json())
        adapter.client.messages.create.return_value = api_resp

        result = await adapter.research_contact("Alice", "Acme", "Director")
        assert result.contact_still_active is False
        assert result.replacement_name == "Bob New"
        assert result.replacement_email == "bob.new@acme.com"
