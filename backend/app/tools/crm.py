"""
CRM tool surface for agents.

Tenant-aware: each call resolves the tenant's HubSpot token from
integration_credentials via app.services.credentials. Falls back to
settings.HUBSPOT_ACCESS_TOKEN only in DEBUG mode.
"""
import sys
import asyncio
from typing import Any

from ..integrations.hubspot import HubSpotConnector
from ..services.credentials import get_hubspot_token


def _ensure_windows_loop_policy() -> None:
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(
                asyncio.WindowsSelectorEventLoopPolicy()
            )
        except Exception:
            pass


async def _connector(tenant_id: str | None) -> HubSpotConnector:
    _ensure_windows_loop_policy()
    token = await get_hubspot_token(tenant_id)
    return HubSpotConnector(access_token=token)


async def search_contacts(
    tenant_id: str | None = None,
    query: str = "",
    limit: int = 10,
) -> list[dict[str, Any]]:
    c = await _connector(tenant_id)
    return await c.search_contacts(query=query, limit=limit)


async def get_contact(
    tenant_id: str | None = None,
    contact_id: str = "",
) -> dict[str, Any] | None:
    c = await _connector(tenant_id)
    return await c.get_contact(contact_id)


async def create_task(
    tenant_id: str | None = None,
    subject: str = "",
    body: str = "",
    contact_id: str | None = None,
    due_at: str | None = None,
) -> dict[str, Any]:
    c = await _connector(tenant_id)
    return await c.create_task(
        subject=subject,
        body=body,
        contact_id=contact_id,
        due_at=due_at,
    )


def format_contacts(contacts: list[dict[str, Any]]) -> str:
    """Render contacts as a compact block for the LLM prompt."""
    if not contacts:
        return "(no contacts returned by CRM)"
    lines = []
    for c in contacts:
        p = c.get("properties", {}) or {}
        lines.append(
            f"- id={c.get('id')} | "
            f"name={p.get('firstname','')} {p.get('lastname','')} | "
            f"email={p.get('email','')} | "
            f"company={p.get('company','')} | "
            f"title={p.get('jobtitle','')} | "
            f"lifecycle={p.get('lifecyclestage','')} | "
            f"created={p.get('createdate','')}"
        )
    return "\n".join(lines)
