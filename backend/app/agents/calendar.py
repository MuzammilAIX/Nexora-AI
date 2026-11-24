"""Calendar Agent.

Reads today's/this week's calendar on request; proposes meetings that require
approval (per business doc Section 7.3: "Send external emails / create calendar
events: Approval by default for initial release").

Mirrors SupportAgent's contract:
  - read path  -> AgentOutput(success=True, result={..., "requires_approval": False})
  - write path -> AgentOutput(success=True, result={..., "requires_approval": True,
                                                  "action_kind": "calendar_create_event",
                                                  "proposed_action": {...}})
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, ConfigDict, Field

from .base import BaseAgent, AgentInput, AgentOutput
from ..config import settings
from ..tools.calendar import list_events, format_events
from ..tools.schedule import local_tz, local_tz_name


# ------------------------------------------------------------------ schemas


class CalendarRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: str = Field(
        description="One of: 'list' (read schedule) or 'create' (propose meeting)"
    )
    when: str = Field(
        default="today",
        description="For intent=list: 'today', 'tomorrow', 'week', or ISO date YYYY-MM-DD"
    )
    summary: str = Field(
        default="",
        description="For intent=create: meeting title/subject"
    )
    start_iso: str = Field(
        default="",
        description="For intent=create: ISO datetime e.g. 2026-11-24T14:00:00+00:00"
    )
    end_iso: str = Field(
        default="",
        description="For intent=create: ISO datetime e.g. 2026-11-24T14:30:00+00:00"
    )
    attendees: list[str] = Field(
        default_factory=list,
        description="Email addresses to invite"
    )
    description: str = Field(
        default="",
        description="Optional meeting description"
    )


def _build_system_prompt() -> str:
    now = datetime.now(local_tz())
    return (
        "You are Nexora AI's calendar specialist. Classify the user's request "
        "into one of two intents and fill the matching fields.\n\n"
        "INTENT = 'list': the user is asking what's on their schedule. "
        "Fill `when` with 'today', 'tomorrow', 'week', or an explicit ISO date. "
        "Leave all create-fields empty.\n\n"
        "INTENT = 'create': the user wants to schedule a meeting. "
        "Fill `summary` (short title), `start_iso`, `end_iso`, "
        "`attendees` (email addresses from the request) and optional `description`.\n\n"
        "TIME RULES: every time the user mentions is in THEIR local timezone, "
        + local_tz_name() + ". Output start_iso and end_iso as ISO 8601 with that "
        "timezone's UTC offset, for example " + now.replace(microsecond=0).isoformat() + ". "
        "If no time is given, use tomorrow at 10:00 local time for 30 minutes.\n\n"
        "Current local date and time: " + now.strftime("%A %Y-%m-%d %H:%M")
    )


def _extract_email_addresses(text: str) -> list[str]:
    return re.findall(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", text or "")


# ------------------------------------------------------------------ agent


class CalendarAgent(BaseAgent):
    name = "calendar"

    async def run(self, payload: AgentInput) -> AgentOutput:
        try:
            context = payload.context or {}
            tenant_id = context.get("tenant_id")
            user_request = (
                context.get("user_request")
                or payload.task_description
                or ""
            )

            if not tenant_id:
                return AgentOutput(
                    success=False,
                    error="calendar agent requires tenant_id in context",
                )

            # 1. Parse intent via LLM with structured output
            llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY,
                timeout=60,
                max_retries=2,
            ).with_structured_output(CalendarRequest)

            parsed: CalendarRequest = await llm.ainvoke([
                SystemMessage(content=_build_system_prompt()),
                HumanMessage(content=user_request or "what's on my calendar today?"),
            ])

            # 2. Read path — list events, no approval
            if parsed.intent == "list":
                events = await list_events(
                    tenant_id=tenant_id,
                    when=parsed.when or "today",
                )
                return AgentOutput(
                    success=True,
                    result={
                        "action": "calendar_list",
                        "when": parsed.when or "today",
                        "count": len(events),
                        "events": events,
                        "formatted": format_events(events),
                        "requires_approval": False,
                    },
                )

            # 3. Write path — propose meeting, requires approval
            # If no explicit time was given, default to tomorrow 10:00 UTC, 30min.
            summary = parsed.summary or "Meeting"
            start_iso = parsed.start_iso
            end_iso = parsed.end_iso
            if not start_iso or not end_iso:
                tomorrow = (datetime.now(local_tz()) + timedelta(days=1)).replace(
                    hour=10, minute=0, second=0, microsecond=0
                )
                start_iso = tomorrow.isoformat()
                end_iso = (tomorrow + timedelta(minutes=30)).isoformat()

            # Extract any raw emails from the request as fallback attendees
            attendees = parsed.attendees or []
            if not attendees:
                attendees = _extract_email_addresses(user_request)

            proposed_action = {
                "summary": summary,
                "start_iso": start_iso,
                "end_iso": end_iso,
                "attendees": attendees,
                "description": parsed.description or "",
            }

            return AgentOutput(
                success=True,
                result={
                    "action": "calendar_create_prepared",
                    "summary": summary,
                    "start_iso": start_iso,
                    "end_iso": end_iso,
                    "attendees": attendees,
                    "description": parsed.description or "",
                    "action_kind": "calendar_create_event",
                    "requires_approval": True,
                    "approval_reason": (
                        f"Creating calendar event '{summary}' "
                        f"with {len(attendees)} attendee(s)"
                    ),
                    "proposed_action": proposed_action,
                },
            )

        except Exception as exc:
            return AgentOutput(
                success=False,
                error=f"calendar agent failed: {exc}",
            )


__all__ = ["CalendarAgent", "CalendarRequest"]
