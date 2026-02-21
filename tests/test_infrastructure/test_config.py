"""
Tests for Config.from_env().
Uses monkeypatch to control environment variables without polluting the real env.
"""

import pytest

from prospectkeeper.infrastructure.config import Config


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

REQUIRED_ENV = {
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_SERVICE_KEY": "service-key-123",
    "ANTHROPIC_API_KEY": "sk-ant-test",
    "LANGFUSE_PUBLIC_KEY": "pk-langfuse-test",
    "LANGFUSE_SECRET_KEY": "sk-langfuse-test",
}


def set_required_env(monkeypatch):
    """Set all required environment variables."""
    for key, val in REQUIRED_ENV.items():
        monkeypatch.setenv(key, val)


# ─────────────────────────────────────────────────────────────────────────────
# Successful construction
# ─────────────────────────────────────────────────────────────────────────────


class TestConfigFromEnvSuccess:
    def test_creates_config_with_all_required_vars(self, monkeypatch):
        set_required_env(monkeypatch)
        config = Config.from_env()
        assert config.supabase_url == "https://test.supabase.co"
        assert config.supabase_service_key == "service-key-123"
        assert config.anthropic_api_key == "sk-ant-test"
        assert config.langfuse_public_key == "pk-langfuse-test"
        assert config.langfuse_secret_key == "sk-langfuse-test"

    def test_batch_limit_defaults_to_50(self, monkeypatch):
        set_required_env(monkeypatch)
        monkeypatch.delenv("BATCH_LIMIT", raising=False)
        config = Config.from_env()
        assert config.batch_limit == 50

    def test_batch_limit_read_from_env(self, monkeypatch):
        set_required_env(monkeypatch)
        monkeypatch.setenv("BATCH_LIMIT", "100")
        config = Config.from_env()
        assert config.batch_limit == 100

    def test_batch_concurrency_defaults_to_5(self, monkeypatch):
        set_required_env(monkeypatch)
        monkeypatch.delenv("BATCH_CONCURRENCY", raising=False)
        config = Config.from_env()
        assert config.batch_concurrency == 5

    def test_batch_concurrency_read_from_env(self, monkeypatch):
        set_required_env(monkeypatch)
        monkeypatch.setenv("BATCH_CONCURRENCY", "10")
        config = Config.from_env()
        assert config.batch_concurrency == 10

    def test_config_is_frozen_dataclass(self, monkeypatch):
        """Config must be immutable — writing to a field raises FrozenInstanceError."""
        set_required_env(monkeypatch)
        config = Config.from_env()
        with pytest.raises(Exception):  # FrozenInstanceError is a subclass of AttributeError
            config.supabase_url = "something-else"  # type: ignore


# ─────────────────────────────────────────────────────────────────────────────
# Missing required variables
# ─────────────────────────────────────────────────────────────────────────────


class TestConfigFromEnvMissingRequired:
    @pytest.mark.parametrize("missing_key", [
        "SUPABASE_URL",
        "SUPABASE_SERVICE_KEY",
        "ANTHROPIC_API_KEY",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
    ])
    def test_raises_environment_error_for_each_required_key(
        self, missing_key, monkeypatch
    ):
        set_required_env(monkeypatch)
        monkeypatch.delenv(missing_key)
        with pytest.raises(EnvironmentError):
            Config.from_env()

    @pytest.mark.parametrize("missing_key", [
        "SUPABASE_URL",
        "SUPABASE_SERVICE_KEY",
        "ANTHROPIC_API_KEY",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
    ])
    def test_error_message_names_the_missing_variable(
        self, missing_key, monkeypatch
    ):
        set_required_env(monkeypatch)
        monkeypatch.delenv(missing_key)
        with pytest.raises(EnvironmentError, match=missing_key):
            Config.from_env()

    def test_error_message_lists_all_missing_when_multiple_absent(self, monkeypatch):
        """When multiple required vars are absent, all appear in the error."""
        # Clear all required vars
        for key in REQUIRED_ENV:
            monkeypatch.delenv(key, raising=False)

        with pytest.raises(EnvironmentError) as exc_info:
            Config.from_env()

        error_msg = str(exc_info.value)
        for key in REQUIRED_ENV:
            assert key in error_msg

    def test_error_hints_at_env_file(self, monkeypatch):
        set_required_env(monkeypatch)
        monkeypatch.delenv("SUPABASE_URL")
        with pytest.raises(EnvironmentError, match=r"\.env"):
            Config.from_env()
