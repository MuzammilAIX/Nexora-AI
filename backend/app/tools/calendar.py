"""
Calendar tool surface for agents.

Routes through CalendarConnector(tenant_id=...), which loads encrypted tokens
from oauth_tokens.load_tokens and handles automatic refresh.

Public API:
  list_events(tenant_id, when)            # read-only, no approval
  create_event(tenant_id, ...)            # WRITE — approval-gated
  format_events(events)
  format_event(event)
"""
from __future__ import annotations

import sys
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

from ..integrations.calendar import CalendarConnector, CalendarNotConnected
from .schedule import local_tz, local_tz_name


def _ensure_windows_loop_policy() -> None:
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except Exception:
            pass


async def _connector(tenant_id: str | None) -> CalendarConnector:
    _ensure_windows_loop_policy()
    if not tenant_id:
        raise CalendarNotConnected("tenant_id is required for Calendar operations")
    return CalendarConnector(tenant_id=str(tenant_id))


async def list_events(
    tenant_id: str | None = None,
    when: str = "today",
    tz: str | None = None,
) -> list[dict[str, Any]]:
    """Read-only. `when`: 'today' | 'tomorrow' | 'week' | ISO date."""
    c = await _connector(tenant_id)
    now = datetime.now(local_tz())
    if when == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
    elif when == "tomorrow":
        start = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end = start + timedelta(days=1)
    elif when == "week":
        start = now
        end = now + timedelta(days=7)
    else:
        try:
            start = datetime.fromisoformat(when).replace(tzinfo=local_tz())
        except ValueError:
            start = now
        end = start + timedelta(days=1)

    return await c.list_events(
        time_min=start.isoformat(),
        time_max=end.isoformat(),
    )


async def create_event(
    tenant_id: str | None = None,
    summary: str = "",
    start_iso: str = "",
    end_iso: str = "",
    attendees: list[str] | None = None,
    description: str = "",
    tz: str | None = None,
) -> dict[str, Any]:
    """DANGER: Only call from the approval executor, NEVER from the agent."""
    c = await _connector(tenant_id)
    return await c.create_event(
        summary=summary,
        start_iso=start_iso,
        end_iso=end_iso,
        attendees=attendees or [],
        description=description,
        timezone_str=tz or local_tz_name(),
    )


def format_events(events: list[dict[str, Any]]) -> str:
    if not events:
        return "(no events)"
    lines = []
    for e in events:
        start = (
            e.get("start", {}).get("dateTime")
            or e.get("start", {}).get("date")
            or ""
        )
        end = (
            e.get("end", {}).get("dateTime")
            or e.get("end", {}).get("date")
            or ""
        )
        attendees = [a.get("email", "") for a in e.get("attendees", [])]
        lines.append(
            f"- {start} -> {end} | {e.get('summary', '(no title)')}"
            f" | attendees={attendees} | id={e.get('id')}"
        )
    return "\n".join(lines)


def format_event(event: dict[str, Any] | None) -> str:
    if not event:
        return "(no event)"
    start = event.get("start", {}).get("dateTime", "")
    end = event.get("end", {}).get("dateTime", "")
    return (
        f"Title: {event.get('summary', '')}\n"
        f"Start: {start}\n"
        f"End:   {end}\n"
        f"Attendees: {[a.get('email') for a in event.get('attendees', [])]}\n"
        f"Link: {event.get('htmlLink', '')}"
    )
