"""
Provider-independent email connector interface.

Agents call these methods; concrete connectors implement them
(Gmail today, others later). Provider-specific HTTP, auth, retries
live inside the subclass - never leak to the agent layer.
"""
from abc import ABC, abstractmethod
from typing import Any


class EmailConnector(ABC):
    provider: str

    @abstractmethod
    async def search_emails(
        self, query: str = "", max_results: int = 20
    ) -> list[dict[str, Any]]:
        """Return up to max_results emails matching query (empty query = recent unread)."""

    @abstractmethod
    async def get_email(self, message_id: str) -> dict[str, Any] | None:
        """Fetch one email by provider id. Return None if not found."""

    @abstractmethod
    async def draft_reply(
        self, thread_id: str, body: str
    ) -> dict[str, Any]:
        """Create a draft reply in the thread. Does NOT send."""

    @abstractmethod
    async def send_draft(self, draft_id: str) -> dict[str, Any]:
        """Send an approved draft. Only called after human approval."""
