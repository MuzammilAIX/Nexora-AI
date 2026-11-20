"""
Provider-independent CRM connector interface.

Agents call these methods; concrete connectors implement them
(HubSpot today, others later). Provider-specific HTTP, auth, retries
live inside the subclass — never leak to the agent layer.
"""
from abc import ABC, abstractmethod
from typing import Any


class CRMConnector(ABC):
    provider: str

    @abstractmethod
    async def search_contacts(
        self, query: str = "", limit: int = 10
    ) -> list[dict[str, Any]]:
        """Return up to `limit` contacts matching `query` (empty query = recent)."""

    @abstractmethod
    async def get_contact(self, contact_id: str) -> dict[str, Any] | None:
        """Fetch one contact by provider id. Return None if not found."""

    @abstractmethod
    async def create_task(
        self,
        subject: str,
        body: str,
        contact_id: str | None = None,
        due_at: str | None = None,
    ) -> dict[str, Any]:
        """Create a follow-up task, optionally linked to a contact."""
