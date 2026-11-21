"""
Gmail tool surface for agents.

Routes through GmailConnector(tenant_id=...), which loads encrypted tokens
from oauth_tokens.load_tokens and handles automatic refresh.

Public API (same as before so agents don't change):
  search_emails(tenant_id, query, limit)
  get_email(tenant_id, message_id)
  draft_reply(tenant_id, thread_id, body)   # body is "To: ...\nSubject: ...\n\n<text>"
  send_approved_draft(tenant_id, draft_id)
  format_emails(emails)
  format_email(email)
"""
import sys
import asyncio
from typing import Any

from ..integrations.gmail import GmailConnector, GmailNotConnected
from ..integrations.oauth_tokens import load_tokens


def _ensure_windows_loop_policy() -> None:
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except Exception:
            pass


async def _connector(tenant_id: str | None) -> GmailConnector:
    """Return a GmailConnector bound to this tenant's encrypted tokens."""
    _ensure_windows_loop_policy()
    if not tenant_id:
        raise GmailNotConnected("tenant_id is required for Gmail operations")
    tokens = await load_tokens(tenant_id=tenant_id, provider="gmail")
    if tokens is None:
        raise GmailNotConnected(
            f"Gmail is not connected for tenant {tenant_id}. "
            f"Visit /api/v1/integrations/gmail/connect to authorize."
        )
    return GmailConnector(tenant_id=tenant_id)


async def search_emails(
    tenant_id: str | None = None,
    query: str = "",
    limit: int = 10,
) -> list[dict[str, Any]]:
    c = await _connector(tenant_id)
    return await c.search_messages(query=query, max_results=limit)


async def get_email(
    tenant_id: str | None = None,
    message_id: str = "",
) -> dict[str, Any] | None:
    c = await _connector(tenant_id)
    return await c.get_message(message_id)


def _parse_email_string(body: str) -> tuple[str, str, str]:
    """Parse 'To: <addr>\\nSubject: <line>\\n\\n<text>' into (to, subject, text)."""
    to = ""
    subject = ""
    text = ""
    if "\n\n" in body:
        headers_part, text = body.split("\n\n", 1)
    else:
        headers_part = body
    for line in headers_part.splitlines():
        low = line.lower()
        if low.startswith("to:"):
            to = line.split(":", 1)[1].strip()
        elif low.startswith("subject:"):
            subject = line.split(":", 1)[1].strip()
    return to, subject, text


async def draft_reply(
    tenant_id: str | None = None,
    thread_id: str = "",
    body: str = "",
) -> dict[str, Any]:
    """Create a Gmail draft. Parses To/Subject/body from the body string."""
    c = await _connector(tenant_id)
    to, subject, text = _parse_email_string(body)
    if not to or not subject:
        raise ValueError(
            "draft_reply body must contain 'To: <addr>' and 'Subject: <line>'"
        )
    return await c.create_draft(
        to=to,
        subject=subject,
        body=text or body,
        thread_id=thread_id or None,
    )


async def send_approved_draft(
    tenant_id: str | None = None,
    draft_id: str = "",
) -> dict[str, Any]:
    """
    DANGER: Only call this from the approval executor, NEVER from the agent.
    """
    c = await _connector(tenant_id)
    return await c.send_draft(draft_id)


def format_emails(emails: list[dict[str, Any]]) -> str:
    if not emails:
        return "(no emails)"
    lines = []
    for e in emails:
        lines.append(
            f"- id={e.get('id')} | from={e.get('from')} | "
            f"subject={e.get('subject')} | date={e.get('date')}"
        )
    return "\n".join(lines)


def format_email(email: dict[str, Any] | None) -> str:
    if not email:
        return "(no email)"
    return (
        f"From: {email.get('from')}\n"
        f"To: {email.get('to')}\n"
        f"Subject: {email.get('subject')}\n"
        f"Date: {email.get('date')}\n\n"
        f"{email.get('body','')}"
    )
