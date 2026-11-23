"""Bulk email tool. Sends N personalized emails through Gmail with one approval."""
from __future__ import annotations
import sys, asyncio
from typing import Any

from ..integrations.gmail import GmailConnector, GmailNotConnected
from ..integrations.oauth_tokens import load_tokens


def _ensure_windows_loop_policy():
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except Exception:
            pass


async def _connector(tenant_id: str | None) -> GmailConnector:
    _ensure_windows_loop_policy()
    if not tenant_id:
        raise GmailNotConnected("tenant_id required for bulk email")
    tokens = await load_tokens(tenant_id=tenant_id, provider="gmail")
    if not tokens:
        raise GmailNotConnected(f"Gmail not connected for tenant {tenant_id}")
    return GmailConnector(tenant_id=str(tenant_id))


async def send_campaign(
    tenant_id: str | None = None,
    campaign: list[dict[str, Any]] | None = None,
    test_recipient: str | None = None,
) -> dict[str, Any]:
    """
    Send N emails. Each campaign item: {to, subject, body}.
    If test_recipient is set, ALL sends redirect there (safety).
    Returns per-recipient result.
    """
    if not campaign:
        return {"sent": 0, "failed": 0, "details": [], "errors": []}

    c = await _connector(tenant_id)
    sent: list[dict] = []
    failed: list[dict] = []

    for msg in campaign:
        to_addr = test_recipient or msg.get("to", "")
        try:
            r = await c.send_message(
                to=to_addr,
                subject=msg.get("subject", ""),
                body=msg.get("body", ""),
            )
            sent.append({
                "to": to_addr,
                "original_to": msg.get("to"),
                "message_id": r.get("id"),
            })
        except Exception as exc:
            failed.append({
                "to": to_addr,
                "original_to": msg.get("to"),
                "error": str(exc),
            })

    return {
        "sent": len(sent),
        "failed": len(failed),
        "details": sent,
        "errors": failed,
        "test_recipient": test_recipient,
    }


__all__ = ["send_campaign"]
