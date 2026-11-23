"""Bulk email agent. Personalizes one message per recipient, gated by approval."""
from __future__ import annotations
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, ConfigDict, Field

from .base import BaseAgent, AgentInput, AgentOutput
from ..config import settings
from ..tools.users import list_tenant_users


class PersonalizedEmail(BaseModel):
    model_config = ConfigDict(extra="forbid")
    to: str = Field(description="Recipient email exactly as given")
    subject: str = Field(description="Email subject line")
    body: str = Field(description="Full email body, professional tone, personalized")
    personalization_note: str = Field(
        default="", description="What was personalized and why (1 short sentence)"
    )


class CampaignBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    emails: list[PersonalizedEmail]


class BulkEmailAgent(BaseAgent):
    name = "bulk_email"

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
                return AgentOutput(success=False, error="tenant_id required")

            # Resolve recipients — from context (explicit list) or from DB (all users)
            recipients = context.get("recipients")
            if not recipients:
                recipients = await list_tenant_users(tenant_id)
            if not recipients:
                return AgentOutput(
                    success=False,
                    error="No recipients found (no users in tenant or explicit list not provided).",
                )

            # Safety flag from context
            test_recipient = context.get("test_recipient")  # e.g. "me@test.com"

            # Build a compact recipient block for the LLM
            recipient_lines = []
            for r in recipients:
                recipient_lines.append(
                    f"- email={r.get('email')} | name={r.get('name','')} | role={r.get('role','')}"
                )
            recipient_block = "\n".join(recipient_lines)

            llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY,
                timeout=180,
                max_retries=2,
            ).with_structured_output(CampaignBundle)

            parsed: CampaignBundle = await llm.ainvoke([
                SystemMessage(content=(
                    "You are Nexora AI's bulk email specialist. "
                    "Generate ONE personalized email for each recipient below, tailored to "
                    "their role and name. Do NOT invent facts about the user's intent. "
                    "Do not send anything — you are drafting only. "
                    "Return exactly one email per recipient, with `to` set to that recipient's email address.\n\n"
                    "USER INTENT:\n" + user_request + "\n\n"
                    "RECIPIENTS:\n" + recipient_block
                )),
                HumanMessage(content="Generate one personalized email per recipient now."),
            ])

            # Build preview list — preserve original recipient (for redirect safety)
            campaign = []
            valid_emails = {r["email"].lower() for r in recipients}
            for e in parsed.emails:
                if e.to.lower() not in valid_emails:
                    # LLM hallucinated a recipient not in the list — skip
                    continue
                campaign.append({
                    "to": e.to,
                    "subject": e.subject,
                    "body": e.body,
                    "personalization_note": e.personalization_note or "",
                })

            if not campaign:
                return AgentOutput(
                    success=False,
                    error="LLM returned no valid recipients from the provided list.",
                )

            approval_reason = (
                f"Send {len(campaign)} personalized email(s)"
            )
            if test_recipient:
                approval_reason += f" (TEST MODE — all redirected to {test_recipient})"

            return AgentOutput(
                success=True,
                result={
                    "requires_approval": True,
                    "action_kind": "bulk_email_send",
                    "campaign_preview": campaign,
                    "recipient_count": len(campaign),
                    "test_recipient": test_recipient,
                    "approval_reason": approval_reason,
                },
            )

        except Exception as exc:
            return AgentOutput(success=False, error=f"bulk_email failed: {exc}")


__all__ = ["BulkEmailAgent", "CampaignBundle", "PersonalizedEmail"]
