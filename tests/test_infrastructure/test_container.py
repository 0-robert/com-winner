"""
Tests for the DI Container.

All external adapters (Supabase, Claude) require real credentials in their
constructors, so we patch them to avoid network calls or crashes.
The goal is to verify that Container wires up the full object graph and
exposes the expected attributes.
"""

import pytest
from unittest.mock import MagicMock, patch

from prospectkeeper.infrastructure.config import Config


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

FAKE_CONFIG = Config(
    supabase_url="https://fake.supabase.co",
    supabase_service_key="fake-service-key",
    anthropic_api_key="sk-ant-fake",
    helicone_api_key="sk-helicone-fake",
    zerobounce_api_key="zb-fake",
    batch_limit=50,
    batch_concurrency=5,
)


def make_container():
    """Build a Container with all network-touching adapters patched."""
    with patch("prospectkeeper.infrastructure.container.SupabaseAdapter") as mock_sb:
        with patch("prospectkeeper.infrastructure.container.ClaudeAdapter") as mock_claude:
            mock_sb.return_value = MagicMock()
            mock_claude.return_value = MagicMock()

            from prospectkeeper.infrastructure.container import Container
            container = Container(FAKE_CONFIG)

    return container


# ─────────────────────────────────────────────────────────────────────────────
# Container wiring
# ─────────────────────────────────────────────────────────────────────────────


class TestContainerWiring:
    def test_container_has_repository(self):
        container = make_container()
        assert container.repository is not None

    def test_container_has_scraper(self):
        container = make_container()
        assert container.scraper is not None

    def test_container_has_email_verifier(self):
        container = make_container()
        assert container.email_verifier is not None

    def test_container_has_linkedin(self):
        container = make_container()
        assert container.linkedin is not None

    def test_container_has_ai(self):
        container = make_container()
        assert container.ai is not None

    def test_container_has_verify_use_case(self):
        container = make_container()
        assert container.verify_use_case is not None

    def test_container_has_roi_use_case(self):
        container = make_container()
        assert container.roi_use_case is not None

    def test_container_has_process_batch_use_case(self):
        container = make_container()
        assert container.process_batch_use_case is not None

    def test_config_stored_on_container(self):
        container = make_container()
        assert container.config is FAKE_CONFIG

    def test_process_batch_use_case_uses_same_repository(self):
        """process_batch_use_case.repository should be the same object as container.repository."""
        container = make_container()
        assert container.process_batch_use_case.repository is container.repository

    def test_verify_use_case_uses_same_scraper(self):
        container = make_container()
        assert container.verify_use_case.scraper is container.scraper

    def test_verify_use_case_uses_same_ai(self):
        container = make_container()
        assert container.verify_use_case.ai is container.ai
