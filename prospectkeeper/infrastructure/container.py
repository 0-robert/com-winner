"""
Dependency Injection Container.
Wires all adapters to their interfaces and composes use cases.
This is the ONLY place that knows about concrete implementations.
The domain and use case layers remain framework-agnostic.
"""

from .config import Config
from ..adapters.supabase_adapter import SupabaseAdapter
from ..adapters.bs4_scraper_adapter import BS4ScraperAdapter
from ..adapters.zerobounce_adapter import ZeroBounceAdapter
from ..adapters.claude_adapter import ClaudeAdapter
from ..adapters.email_sender_adapter import EmailSenderAdapter
from ..use_cases.verify_contact import VerifyContactUseCase
from ..use_cases.calculate_roi import CalculateROIUseCase
from ..use_cases.process_batch import ProcessBatchUseCase


class Container:
    """
    Composes the full application object graph.
    Swap any adapter by changing a single line here.
    """

    def __init__(self, config: Config):
        self.config = config

        # ── Adapters (Ports & Adapters layer) ─────────────────────────────
        self.repository = SupabaseAdapter(
            url=config.supabase_url,
            key=config.supabase_service_key,
        )
        self.scraper = BS4ScraperAdapter()
        self.email_verifier = ZeroBounceAdapter(api_key=config.zerobounce_api_key)
        self.email_sender = EmailSenderAdapter()
        self.ai = ClaudeAdapter(
            anthropic_api_key=config.anthropic_api_key,
        )

        # ── Use Cases (Application layer) ──────────────────────────────────
        self.verify_use_case = VerifyContactUseCase(
            scraper=self.scraper,
            ai=self.ai,
            email_verifier=self.email_verifier,
            email_sender=self.email_sender,
        )
        self.roi_use_case = CalculateROIUseCase()
        self.process_batch_use_case = ProcessBatchUseCase(
            repository=self.repository,
            verify_use_case=self.verify_use_case,
            roi_use_case=self.roi_use_case,
        )
