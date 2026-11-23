"""Google Calendar connector: read events + create events via Calendar API v3.

Tokens come from app.integrations.oauth_tokens (encrypted at rest).
Shares the same provider row as Gmail ('gmail') — Google scopes are stored
in a single blob, so Calendar reuses the existing integration.

Scope requirements (add to OAuth consent screen):
  https://www.googleapis.com/auth/calendar.readonly
  https://www.googleapis.com/auth/calendar.events
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import settings
from app.integrations.oauth_tokens import load_tokens, rotate_access_token

logger = logging.getLogger(__name__)

PROVIDER = "gmail"  # same integration row as Gmail — one Google connection


class CalendarNotConnected(RuntimeError):
    """Raised when no Google integration exists for the tenant."""


class CalendarConnector:
    def __init__(self, tenant_id: str):
        self.tenant_id = str(tenant_id)

    # ------------------------------------------------------------- auth

    async def _get_credentials(self) -> Credentials:
        tokens = await load_tokens(tenant_id=self.tenant_id, provider=PROVIDER)
        if not tokens:
            raise CalendarNotConnected(
                f"Google not connected for tenant {self.tenant_id}. "
                f"Visit /api/v1/integrations/gmail/connect to authorize."
            )

        creds = Credentials(
            token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=tokens.get("scopes") or None,
        )
        exp = tokens.get("expires_at")
        if exp:
            try:
                creds.expiry = datetime.fromisoformat(exp).astimezone(timezone.utc).replace(tzinfo=None)
            except (ValueError, TypeError):
                pass

        if not creds.valid:
            if not creds.refresh_token:
                raise CalendarNotConnected(
                    "Google access token expired and no refresh_token stored. "
                    "Re-run /api/v1/integrations/gmail/connect."
                )
            creds.refresh(GoogleRequest())
            await rotate_access_token(
                tenant_id=self.tenant_id,
                provider=PROVIDER,
                new_access_token=creds.token,
                new_expires_at=creds.expiry.replace(tzinfo=timezone.utc)
                    if creds.expiry else None,
            )
        return creds

    async def _service(self):
        creds = await self._get_credentials()
        return build("calendar", "v3", credentials=creds, cache_discovery=False)

    # ------------------------------------------------------------- events

    async def list_events(
        self,
        *,
        time_min: str,
        time_max: str,
        max_results: int = 50,
    ) -> list[dict[str, Any]]:
        """List events on the primary calendar between two ISO timestamps."""
        svc = await self._service()
        resp = svc.events().list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        return resp.get("items", [])

    async def create_event(
        self,
        *,
        summary: str,
        start_iso: str,
        end_iso: str,
        attendees: list[str] | None = None,
        description: str = "",
        timezone_str: str = "UTC",
        send_updates: str = "all",
    ) -> dict[str, Any]:
        """Create an event on the primary calendar.

        DANGER: call only from the approval executor — not from the agent.
        """
        svc = await self._service()
        body: dict[str, Any] = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start_iso, "timeZone": timezone_str},
            "end": {"dateTime": end_iso, "timeZone": timezone_str},
        }
        if attendees:
            body["attendees"] = [{"email": e} for e in attendees]
        try:
            return svc.events().insert(
                calendarId="primary",
                body=body,
                sendUpdates=send_updates,
            ).execute()
        except HttpError as exc:
            logger.error("calendar.create_event failed: %s", exc)
            raise


__all__ = ["CalendarConnector", "CalendarNotConnected", "PROVIDER"]
