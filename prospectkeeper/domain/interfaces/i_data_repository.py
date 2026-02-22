"""
IDataRepository - Port: defines the data persistence contract.
The domain doesn't know about Supabase, PostgreSQL, or any ORM.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..entities.contact import Contact
from ..entities.verification_result import VerificationResult
from ..entities.agent_economics import ValueProofReceipt


class IDataRepository(ABC):
    """Port for reading and writing Contact data."""

    @abstractmethod
    async def get_all_contacts(self) -> List[Contact]:
        """Retrieve all contacts from the data store."""
        pass

    @abstractmethod
    async def get_contacts_for_verification(self, limit: int = 50) -> List[Contact]:
        """Retrieve contacts that need verification (not opted-out)."""
        pass

    @abstractmethod
    async def get_contacts_needing_review(self) -> List[Contact]:
        """Retrieve contacts flagged for human review."""
        pass

    @abstractmethod
    async def get_contact_by_id(self, contact_id: str) -> Optional[Contact]:
        pass

    @abstractmethod
    async def save_contact(self, contact: Contact) -> Contact:
        """Upsert a contact record."""
        pass

    @abstractmethod
    async def save_verification_result(self, result: VerificationResult) -> None:
        """Persist the result of a verification run for audit purposes."""
        pass

    @abstractmethod
    async def bulk_update_contacts(self, contacts: List[Contact]) -> None:
        """Batch-update multiple contacts."""
        pass

    @abstractmethod
    async def insert_contact(self, contact: Contact) -> Contact:
        """Insert a brand new replacement contact."""
        pass

    @abstractmethod
    async def get_contact_by_email(self, email: str) -> Optional[Contact]:
        """Look up a contact by their email address."""
        pass

    @abstractmethod
    async def save_batch_receipt(self, receipt: ValueProofReceipt) -> None:
        """Persist the Value-Proof Receipt for a completed batch run."""
        pass
