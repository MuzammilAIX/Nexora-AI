"""
HubSpot CRM connector.

Reads scopes granted to the Service Key:
    crm.objects.contacts.read
    crm.objects.contacts.write
    crm.schemas.contacts.read

Uses the Service Key token passed to __init__, or the one from
settings.HUBSPOT_ACCESS_TOKEN as a fallback for single-tenant dev.
"""
import logging
from typing import Any

import httpx

from ..config import settings
from .base import CRMConnector


log = logging.getLogger(__name__)

HUBSPOT_BASE = "https://api.hubapi.com"
CONTACT_PROPS = [
    "firstname",
    "lastname",
    "email",
    "company",
    "jobtitle",
    "phone",
    "lifecyclestage",
    "createdate",
    "hs_object_id",
]


class HubSpotConnector(CRMConnector):
    provider = "hubspot"

    def __init__(self, access_token: str | None = None, timeout: float = 15.0):
        token = access_token or settings.HUBSPOT_ACCESS_TOKEN
        if not token:
            raise RuntimeError(
                "HubSpot token missing — set HUBSPOT_ACCESS_TOKEN in .env "
                "or pass access_token explicitly."
            )
        self._token = token
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    async def _request(
        self, method: str, path: str, **kwargs: Any
    ) -> dict[str, Any]:
        url = f"{HUBSPOT_BASE}{path}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.request(
                method, url, headers=self._headers(), **kwargs
            )
        if resp.status_code >= 400:
            log.error(
                "hubspot %s %s -> %s %s",
                method, path, resp.status_code, resp.text[:500],
            )
            resp.raise_for_status()
        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    async def search_contacts(
        self, query: str = "", limit: int = 10
    ) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 100))

        if not query.strip():
            data = await self._request(
                "GET",
                "/crm/v3/objects/contacts",
                params={"limit": limit, "properties": ",".join(CONTACT_PROPS)},
            )
            return data.get("results", [])

        # Search API — free-text match on name/email
        body = {
            "limit": limit,
            "properties": CONTACT_PROPS,
            "filterGroups": [
                {
                    "filters": [
                        {
                            "propertyName": "email",
                            "operator": "CONTAINS_TOKEN",
                            "value": query.strip(),
                        }
                    ]
                }
            ],
        }
        data = await self._request(
            "POST", "/crm/v3/objects/contacts/search", json=body
        )
        return data.get("results", [])

    async def get_contact(self, contact_id: str) -> dict[str, Any] | None:
        try:
            return await self._request(
                "GET",
                f"/crm/v3/objects/contacts/{contact_id}",
                params={"properties": ",".join(CONTACT_PROPS)},
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise

    async def create_task(
        self,
        subject: str,
        body: str,
        contact_id: str | None = None,
        due_at: str | None = None,
    ) -> dict[str, Any]:
        from datetime import datetime, timezone

        # hs_timestamp is REQUIRED by HubSpot. Default to now if caller
        # does not provide a due date.
        if not due_at:
            due_at = datetime.now(timezone.utc).isoformat()

        properties: dict[str, Any] = {
            "hs_task_subject": subject,
            "hs_task_body": body,
            "hs_task_status": "NOT_STARTED",
            "hs_task_type": "TODO",
            "hs_timestamp": due_at,
        }

        payload: dict[str, Any] = {"properties": properties}
        if contact_id:
            payload["associations"] = [
                {
                    "to": {"id": contact_id},
                    "types": [
                        {
                            "associationCategory": "HUBSPOT_DEFINED",
                            "associationTypeId": 204,
                        }
                    ],
                }
            ]

        return await self._request(
            "POST", "/crm/v3/objects/tasks", json=payload
        )
