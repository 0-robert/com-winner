"""
Tests for ZeroBounceAdapter.
All HTTP calls mocked via httpx.AsyncClient patching.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from prospectkeeper.adapters.zerobounce_adapter import ZeroBounceAdapter, COST_PER_CREDIT
from prospectkeeper.domain.interfaces.i_email_verification_gateway import EmailStatus


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def make_zb_response(status: str, sub_status: str = "") -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"status": status, "sub_status": sub_status}
    return resp


def patch_httpx_client(response: MagicMock):
    """Patch httpx.AsyncClient so .get() returns the provided response."""
    client_mock = AsyncMock()
    client_mock.get.return_value = response
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client_mock)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


# ─────────────────────────────────────────────────────────────────────────────
# Missing email / API key — short-circuit (no HTTP call)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestShortCircuit:
    async def test_empty_email_returns_unknown_without_http_call(self):
        adapter = ZeroBounceAdapter(api_key="test-key")
        with patch("prospectkeeper.adapters.zerobounce_adapter.httpx.AsyncClient") as mock_cls:
            result = await adapter.verify_email("")
        mock_cls.assert_not_called()
        assert result.status == EmailStatus.UNKNOWN
        assert result.is_valid is False
        assert result.cost_usd == 0.0
        assert result.error == "Missing email or API key"

    async def test_missing_api_key_returns_unknown_without_http_call(self):
        adapter = ZeroBounceAdapter(api_key="")
        with patch("prospectkeeper.adapters.zerobounce_adapter.httpx.AsyncClient") as mock_cls:
            result = await adapter.verify_email("alice@acme.com")
        mock_cls.assert_not_called()
        assert result.status == EmailStatus.UNKNOWN
        assert result.is_valid is False
        assert result.cost_usd == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Valid API responses — all status mappings
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestStatusMapping:
    @pytest.mark.parametrize("raw_status,expected_status,expected_valid,expected_deliverability", [
        ("valid",       EmailStatus.VALID,       True,  "Deliverable"),
        ("invalid",     EmailStatus.INVALID,     False, "Undeliverable"),
        ("catch-all",   EmailStatus.CATCH_ALL,   False, "Risky"),
        ("unknown",     EmailStatus.UNKNOWN,     False, "Risky"),
        ("spamtrap",    EmailStatus.SPAMTRAP,    False, "Undeliverable"),
        ("abuse",       EmailStatus.ABUSE,       False, "Undeliverable"),
        ("do-not-mail", EmailStatus.DO_NOT_MAIL, False, "Undeliverable"),
    ])
    async def test_status_mapped_correctly(
        self, raw_status, expected_status, expected_valid, expected_deliverability
    ):
        adapter = ZeroBounceAdapter(api_key="key")
        resp = make_zb_response(raw_status)
        cm = patch_httpx_client(resp)

        with patch("prospectkeeper.adapters.zerobounce_adapter.httpx.AsyncClient", return_value=cm):
            result = await adapter.verify_email("alice@acme.com")

        assert result.status == expected_status
        assert result.is_valid == expected_valid
        assert result.deliverability == expected_deliverability

    async def test_unknown_raw_status_maps_to_unknown(self):
        adapter = ZeroBounceAdapter(api_key="key")
        resp = make_zb_response("some-new-status-we-dont-know")
        cm = patch_httpx_client(resp)

        with patch("prospectkeeper.adapters.zerobounce_adapter.httpx.AsyncClient", return_value=cm):
            result = await adapter.verify_email("alice@acme.com")

        assert result.status == EmailStatus.UNKNOWN


@pytest.mark.asyncio
class TestSuccessfulResponse:
    async def test_valid_email_sets_cost(self):
        adapter = ZeroBounceAdapter(api_key="key")
        resp = make_zb_response("valid")
        cm = patch_httpx_client(resp)

        with patch("prospectkeeper.adapters.zerobounce_adapter.httpx.AsyncClient", return_value=cm):
            result = await adapter.verify_email("alice@acme.com")

        assert result.cost_usd == COST_PER_CREDIT

    async def test_email_field_preserved_in_result(self):
        adapter = ZeroBounceAdapter(api_key="key")
        resp = make_zb_response("valid")
        cm = patch_httpx_client(resp)

        with patch("prospectkeeper.adapters.zerobounce_adapter.httpx.AsyncClient", return_value=cm):
            result = await adapter.verify_email("alice@acme.com")

        assert result.email == "alice@acme.com"

    async def test_sub_status_preserved(self):
        adapter = ZeroBounceAdapter(api_key="key")
        resp = make_zb_response("invalid", sub_status="mailbox_not_found")
        cm = patch_httpx_client(resp)

        with patch("prospectkeeper.adapters.zerobounce_adapter.httpx.AsyncClient", return_value=cm):
            result = await adapter.verify_email("alice@acme.com")

        assert result.sub_status == "mailbox_not_found"

    async def test_missing_status_defaults_to_unknown(self):
        adapter = ZeroBounceAdapter(api_key="key")
        client_mock = AsyncMock()
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {}  # No 'status' key
        client_mock.get.return_value = resp
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=client_mock)
        cm.__aexit__ = AsyncMock(return_value=False)

        with patch("prospectkeeper.adapters.zerobounce_adapter.httpx.AsyncClient", return_value=cm):
            result = await adapter.verify_email("alice@acme.com")

        assert result.status == EmailStatus.UNKNOWN


# ─────────────────────────────────────────────────────────────────────────────
# Error handling
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestErrorHandling:
    async def test_timeout_returns_unknown_with_zero_cost(self):
        import httpx as httpx_lib

        adapter = ZeroBounceAdapter(api_key="key")
        client_mock = AsyncMock()
        client_mock.get.side_effect = httpx_lib.TimeoutException("timeout")
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=client_mock)
        cm.__aexit__ = AsyncMock(return_value=False)

        with patch("prospectkeeper.adapters.zerobounce_adapter.httpx.AsyncClient", return_value=cm):
            result = await adapter.verify_email("alice@acme.com")

        assert result.status == EmailStatus.UNKNOWN
        assert result.is_valid is False
        assert result.cost_usd == 0.0
        assert result.error == "Timeout"

    async def test_generic_exception_returns_unknown_with_error_message(self):
        adapter = ZeroBounceAdapter(api_key="key")
        client_mock = AsyncMock()
        client_mock.get.side_effect = ValueError("unexpected response format")
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=client_mock)
        cm.__aexit__ = AsyncMock(return_value=False)

        with patch("prospectkeeper.adapters.zerobounce_adapter.httpx.AsyncClient", return_value=cm):
            result = await adapter.verify_email("alice@acme.com")

        assert result.status == EmailStatus.UNKNOWN
        assert result.cost_usd == 0.0
        assert "unexpected response format" in result.error

    async def test_http_error_returns_unknown(self):
        import httpx as httpx_lib

        adapter = ZeroBounceAdapter(api_key="key")
        client_mock = AsyncMock()
        resp = MagicMock()
        resp.raise_for_status.side_effect = httpx_lib.HTTPStatusError(
            "403", request=MagicMock(), response=MagicMock()
        )
        client_mock.get.return_value = resp
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=client_mock)
        cm.__aexit__ = AsyncMock(return_value=False)

        with patch("prospectkeeper.adapters.zerobounce_adapter.httpx.AsyncClient", return_value=cm):
            result = await adapter.verify_email("alice@acme.com")

        assert result.status == EmailStatus.UNKNOWN
        assert result.cost_usd == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# _map_status unit tests
# ─────────────────────────────────────────────────────────────────────────────


class TestMapStatus:
    def setup_method(self):
        self.adapter = ZeroBounceAdapter(api_key="key")

    @pytest.mark.parametrize("raw,expected", [
        ("valid",        EmailStatus.VALID),
        ("invalid",      EmailStatus.INVALID),
        ("catch-all",    EmailStatus.CATCH_ALL),
        ("unknown",      EmailStatus.UNKNOWN),
        ("spamtrap",     EmailStatus.SPAMTRAP),
        ("abuse",        EmailStatus.ABUSE),
        ("do-not-mail",  EmailStatus.DO_NOT_MAIL),
        ("anything-else",EmailStatus.UNKNOWN),  # fallback
        ("",             EmailStatus.UNKNOWN),  # empty string fallback
    ])
    def test_maps_raw_status_to_enum(self, raw, expected):
        assert self.adapter._map_status(raw) == expected
