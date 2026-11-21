"""Gmail connector: read/search/send via Google Gmail API.

Tokens come from app.integrations.oauth_tokens (encrypted at rest).
Automatic refresh: on 401, the refresh_token from the encrypted blob
is used to obtain a new access_token, which is written back.

Scope requirements:
  https://www.googleapis.com/auth/gmail.readonly
  https://www.googleapis.com/auth/gmail.send
  https://www.googleapis.com/auth/gmail.modify
"""
from __future__ import annotations

import base64
import logging
from datetime import datetime, timezone
from email.mime.text import MIMEText
from typing import Any

from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import settings
from app.integrations.oauth_tokens import load_tokens, rotate_access_token

logger = logging.getLogger(__name__)


PROVIDER = "gmail"


class GmailNotConnected(RuntimeError):
    """Raised when no Gmail integration exists for the tenant."""


class GmailConnector:
    def __init__(self, tenant_id: str):
        self.tenant_id = str(tenant_id)

    # ------------------------------------------------------------- auth

    async def _get_credentials(self) -> Credentials:
        tokens = await load_tokens(tenant_id=self.tenant_id, provider=PROVIDER)
        if not tokens:
            raise GmailNotConnected(
                f"Gmail not connected for tenant {self.tenant_id}. "
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
                raise GmailNotConnected(
                    "Gmail access token expired and no refresh_token stored. "
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
        return build("gmail", "v1", credentials=creds, cache_discovery=False)

    # --------------------------------------------------------- messages

    async def search_messages(
        self, query: str, max_results: int = 10
    ) -> list[dict[str, Any]]:
        """Search messages. Returns [{id, threadId, subject, from, snippet, internalDate}]"""
        svc = await self._service()
        result = svc.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()
        messages = result.get("messages", [])
        out = []
        for m in messages:
            try:
                meta = svc.users().messages().get(
                    userId="me", id=m["id"], format="metadata",
                    metadataHeaders=["Subject", "From", "Date"],
                ).execute()
                headers = {h["name"].lower(): h["value"]
                           for h in meta.get("payload", {}).get("headers", [])}
                out.append({
                    "id": m["id"],
                    "threadId": m.get("threadId"),
                    "subject": headers.get("subject", ""),
                    "from": headers.get("from", ""),
                    "date": headers.get("date", ""),
                    "snippet": meta.get("snippet", ""),
                    "internalDate": meta.get("internalDate"),
                })
            except HttpError as exc:
                logger.warning("metadata fetch failed for %s: %s", m["id"], exc)
        return out

    async def get_message(self, message_id: str) -> dict[str, Any]:
        """Fetch a single message with full body + headers."""
        svc = await self._service()
        msg = svc.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute()
        headers = {h["name"].lower(): h["value"]
                   for h in msg.get("payload", {}).get("headers", [])}
        body = self._extract_body(msg.get("payload", {}))
        return {
            "id": msg["id"],
            "threadId": msg.get("threadId"),
            "subject": headers.get("subject", ""),
            "from": headers.get("from", ""),
            "to": headers.get("to", ""),
            "date": headers.get("date", ""),
            "snippet": msg.get("snippet", ""),
            "body": body,
            "internalDate": msg.get("internalDate"),
        }

    @staticmethod
    def _extract_body(payload: dict) -> str:
        """Walk the MIME tree; prefer text/plain, fall back to text/html."""
        def decode(data: str) -> str:
            return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode(
                "utf-8", errors="replace"
            )

        parts = payload.get("parts") or []
        plain, html = "", ""
        for p in parts:
            mime = p.get("mimeType", "")
            data = (p.get("body") or {}).get("data")
            if not data:
                continue
            if mime == "text/plain" and not plain:
                plain = decode(data)
            elif mime == "text/html" and not html:
                html = decode(data)
        if plain:
            return plain
        if html:
            return html
        data = (payload.get("body") or {}).get("data")
        return decode(data) if data else ""

    # ------------------------------------------------------------- send

    async def send_message(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        thread_id: str | None = None,
        from_email: str | None = None,
    ) -> dict[str, Any]:
        """Send an email. Returns {id, threadId}."""
        svc = await self._service()
        msg = MIMEText(body, "plain", "utf-8")
        msg["To"] = to
        msg["Subject"] = subject
        if from_email:
            msg["From"] = from_email

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        send_body: dict[str, Any] = {"raw": raw}
        if thread_id:
            send_body["threadId"] = thread_id

        sent = svc.users().messages().send(userId="me", body=send_body).execute()
        return {"id": sent["id"], "threadId": sent.get("threadId")}

    async def send_draft(self, draft_id: str) -> dict[str, Any]:
        """Send an existing draft by id. Returns {id, threadId}."""
        svc = await self._service()
        sent = svc.users().drafts().send(
            userId="me", body={"id": draft_id}
        ).execute()
        return {"id": sent["id"], "threadId": sent.get("threadId")}

    async def create_draft(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a draft (not sent). Returns {id, message_id, threadId}."""
        svc = await self._service()
        msg = MIMEText(body, "plain", "utf-8")
        msg["To"] = to
        msg["Subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

        message_body: dict[str, Any] = {"raw": raw}
        if thread_id:
            message_body["threadId"] = thread_id

        draft = svc.users().drafts().create(
            userId="me", body={"message": message_body}
        ).execute()
        return {
            "id": draft["id"],
            "message_id": draft["message"]["id"],
            "threadId": draft["message"].get("threadId"),
        }


__all__ = ["GmailConnector", "GmailNotConnected", "PROVIDER"]
