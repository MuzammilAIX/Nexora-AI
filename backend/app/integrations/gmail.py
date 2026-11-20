"""
Gmail connector.

SLICE A1: Dev-mode implementation with realistic mock inbox.
SLICE A2: Replace mocks with real Gmail API calls + OAuth token refresh.

Data shape matches real Gmail API.
"""
import sys
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any


def _ensure_windows_loop_policy() -> None:
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(
                asyncio.WindowsSelectorEventLoopPolicy()
            )
        except Exception:
            pass


_MOCK_INBOX = [
    {
        "id": "msg-001",
        "threadId": "thread-001",
        "snippet": "I purchased premium yesterday but still cannot access the features...",
        "from": "sarah@acmecorp.com",
        "to": "support@yourcompany.com",
        "subject": "Cannot access premium features",
        "date": "2026-11-20T09:15:00Z",
        "body": "Hi team,\n\nI purchased your premium subscription yesterday (order INV-2026-11-1847) but I still cannot access the premium features in my account. I tried logging out and back in but nothing changed. My account email is sarah@acmecorp.com.\n\nPlease help as soon as possible.\n\nThanks,\nSarah Chen",
        "labels": ["INBOX", "UNREAD"],
        "unread": True,
    },
    {
        "id": "msg-002",
        "threadId": "thread-002",
        "snippet": "I was charged twice this month for the same subscription...",
        "from": "mike@talltree.io",
        "to": "billing@yourcompany.com",
        "subject": "Duplicate charge on my account",
        "date": "2026-11-20T10:22:00Z",
        "body": "Hello,\n\nI noticed I was charged twice this month for the same subscription. Both charges are on my card ending in 4421. Order number is INV-2026-11-1847. Could you check and refund the duplicate charge?\n\nThanks,\nMike Rodriguez\nTall Tree Consulting",
        "labels": ["INBOX", "UNREAD"],
        "unread": True,
    },
    {
        "id": "msg-003",
        "threadId": "thread-003",
        "snippet": "Our API integration is failing with 401 errors starting this morning...",
        "from": "ops@techwave.dev",
        "to": "api-support@yourcompany.com",
        "subject": "URGENT: API 401 errors",
        "date": "2026-11-20T08:45:00Z",
        "body": "Hi,\n\nOur integration with your API is failing with 401 errors starting this morning. We are using the same API key as before and it worked yesterday. This is blocking our production system.\n\nAccount: techwave.dev\nAPI key prefix: tw_live_...\n\nPlease respond urgently.\n\nTechWave Operations",
        "labels": ["INBOX", "UNREAD", "IMPORTANT"],
        "unread": True,
    },
    {
        "id": "msg-004",
        "threadId": "thread-004",
        "snippet": "Quick question about upgrading my plan...",
        "from": "alex@startuplabs.co",
        "to": "sales@yourcompany.com",
        "subject": "Question about enterprise plan",
        "date": "2026-11-19T16:30:00Z",
        "body": "Hi,\n\nWe are evaluating your platform for our team of 25 and wanted to ask about the enterprise plan pricing and features. Can we set up a demo call next week?\n\nBest,\nAlex Brown\nStartup Labs",
        "labels": ["INBOX"],
        "unread": False,
    },
]

_DEV_DRAFTS = {}


class GmailConnector:
    provider = "gmail"

    def __init__(self, access_token: str | None = None):
        self.access_token = access_token
        self._dev_mode = not access_token

    async def search_emails(
        self, query: str = "", max_results: int = 20
    ) -> list[dict[str, Any]]:
        _ensure_windows_loop_policy()
        if self._dev_mode:
            emails = [e for e in _MOCK_INBOX if e.get("unread", False)]
            if query:
                q = query.lower()
                emails = [
                    e for e in emails
                    if q in e.get("subject", "").lower()
                    or q in e.get("body", "").lower()
                    or q in e.get("from", "").lower()
                ]
            return emails[:max_results]
        raise NotImplementedError("Real Gmail API not yet wired. Slice A2.")

    async def get_email(self, message_id: str) -> dict[str, Any] | None:
        _ensure_windows_loop_policy()
        if self._dev_mode:
            for e in _MOCK_INBOX:
                if e.get("id") == message_id:
                    return e
            return None
        raise NotImplementedError("Real Gmail API not yet wired. Slice A2.")

    async def draft_reply(
        self, thread_id: str, body: str
    ) -> dict[str, Any]:
        _ensure_windows_loop_policy()
        if self._dev_mode:
            original = None
            for e in _MOCK_INBOX:
                if e.get("threadId") == thread_id:
                    original = e
                    break
            if not original:
                raise ValueError(f"Thread {thread_id} not found")
            draft_id = f"draft-{uuid.uuid4().hex[:8]}"
            draft = {
                "draft_id": draft_id,
                "thread_id": thread_id,
                "to": original["from"],
                "subject": f"Re: {original['subject']}",
                "body": body,
                "status": "draft",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            _DEV_DRAFTS[draft_id] = draft
            return draft
        raise NotImplementedError("Real Gmail API not yet wired. Slice A2.")

    async def send_draft(self, draft_id: str) -> dict[str, Any]:
        _ensure_windows_loop_policy()
        if self._dev_mode:
            draft = _DEV_DRAFTS.get(draft_id)
            if not draft:
                raise ValueError(f"Draft {draft_id} not found")
            draft["status"] = "sent"
            draft["sent_at"] = datetime.now(timezone.utc).isoformat()
            return {
                "draft_id": draft_id,
                "thread_id": draft["thread_id"],
                "status": "sent",
                "sent_at": draft["sent_at"],
            }
        raise NotImplementedError("Real Gmail API not yet wired. Slice A2.")
