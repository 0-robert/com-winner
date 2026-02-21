"""
Configuration — reads all settings from environment variables.
Never hardcodes credentials. Uses python-dotenv for local dev.
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    # Supabase
    supabase_url: str
    supabase_service_key: str  # Service role key (backend only, never exposed to frontend)

    # External APIs
    anthropic_api_key: str
    helicone_api_key: str
    zerobounce_api_key: str

    # Agent settings
    batch_limit: int = 50
    batch_concurrency: int = 5

    @classmethod
    def from_env(cls) -> "Config":
        missing = []
        required = [
            "SUPABASE_URL",
            "SUPABASE_SERVICE_KEY",
            "ANTHROPIC_API_KEY",
            "HELICONE_API_KEY",
        ]
        for key in required:
            if not os.getenv(key):
                missing.append(key)

        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                f"Copy .env.example to .env and fill in the values."
            )

        return cls(
            supabase_url=os.environ["SUPABASE_URL"],
            supabase_service_key=os.environ["SUPABASE_SERVICE_KEY"],
            anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
            helicone_api_key=os.environ["HELICONE_API_KEY"],
            zerobounce_api_key=os.getenv("ZEROBOUNCE_API_KEY", ""),
            batch_limit=int(os.getenv("BATCH_LIMIT", "50")),
            batch_concurrency=int(os.getenv("BATCH_CONCURRENCY", "5")),
        )
