"""
Gmail tool surface for agents.

Same shape as crm.py: async functions, tenant_id first, plain dicts,
format_* helpers for prompt rendering.
"""
import sys
import asyncio
from typing import Any

from ..integrations.gmail import GmailConnector
from ..services.credentials import get_gmail_token


def _ensure_windows_loop_policy() -> None:
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(
                asyncio.WindowsSelectorEventLoopPolicy()
            )
        except Exception:
            pass


async def _connector(tenant_id: str | None) -> GmailConnector:
    _ensure_windows_loop_policy()
    try:
        token = await get_gmail_token(tenant_id)
        return GmailConnector(access_token=token)
    except Exception:
        return GmailConnector(access_token=None)


async def search_emails(
    tenant_id: str | None = None,
    query: str = "",
    limit: int = 10,
) -> list[dict[str, Any]]:
    c = await _connector(tenant_id)
    return await c.search_emails(query=query, max_results=limit)


async def get_email(
    tenant_id: str | None = None,
    message_id: str = "",
) -> dict[str, Any] | None:
    c = await _connector(tenant_id)
    return await c.get_email(message_id)


async def draft_reply(
    tenant_id: str | None = None,
    thread_id: str = "",
    body: str = "",
) -> dict[str, Any]:
    c = await _connector(tenant_id)
    return await c.draft_reply(thread_id=thread_id, body=body)


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
