"""Email agent: check requirements → draft → approval gate."""
from __future__ import annotations
import re
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, ConfigDict, Field

from .base import BaseAgent, AgentInput, AgentOutput
from ..config import settings


class EmailDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    to: str = Field(description="Recipient email address or 'unknown'")
    subject: str = Field(description="Email subject line")
    body: str = Field(description="Full email body, professional tone")
    personalization_notes: list[str] = Field(default_factory=list)
    tone: str = Field(default="professional")


class EmailBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    drafts: list[EmailDraft]
    send_ready: bool = True
    warnings: list[str] = Field(default_factory=list)


_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}")


def _extract_email(text: str) -> str | None:
    m = _EMAIL_RE.search(text or "")
    return m.group(0) if m else None


def _has_purpose(text: str) -> bool:
    """True if the request contains a real topic/purpose (not just 'send email')."""
    if not text:
        return False
    # Strip common "send email to X" scaffolding
    stripped = re.sub(r"\b(send|write|draft|compose|email|e-mail|mail|to|please|a|an|the|me|new)\b",
                      " ", text.lower())
    stripped = _EMAIL_RE.sub("", stripped).strip()
    # Need at least 3 meaningful words remaining
    words = [w for w in stripped.split() if len(w) > 2]
    return len(words) >= 3


class EmailAgent(BaseAgent):
    name = "email"

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

            # ---- 1. Requirements check ----
            # Priority: explicit context fields > extracted from request
            recipient = (
                context.get("recipient")
                or context.get("to")
                or _extract_email(user_request)
            )
            purpose = context.get("purpose") or context.get("topic")
            if not purpose:
                # If the request has real content beyond "send email", use it
                if _has_purpose(user_request):
                    purpose = user_request

            tone = context.get("tone") or "professional"

            missing = []
            if not recipient:
                missing.append("recipient")
            if not purpose:
                missing.append("purpose")

            if missing:
                prompts = []
                if "recipient" in missing:
                    prompts.append(
                        "Who should I send this email to? "
                        "Please provide the recipient's email address."
                    )
                if "purpose" in missing:
                    prompts.append(
                        "What is the purpose or topic of this email? "
                        "Please describe what you want to communicate."
                    )
                prompts.append(
                    "Optional: any preferred tone? (professional / formal / friendly / urgent) "
                    "Reply with 'default' to use professional."
                )
                return AgentOutput(
                    success=True,
                    result={
                        "action": "email_needs_input",
                        "missing_fields": missing,
                        "question_prompts": prompts,
                        "requires_approval": False,
                        "gathered_so_far": {
                            "recipient": recipient,
                            "purpose": purpose,
                            "tone": tone,
                        },
                    },
                )

            # ---- 2. Draft via LLM ----
            llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY,
                timeout=90,
                max_retries=2,
            ).with_structured_output(EmailBundle)

            system = (
                "You are Nexora AI's email specialist. "
                "Draft ONE high-quality professional email with the provided details.\n\n"
                "REQUIREMENTS:\n"
                f"- Recipient: {recipient}\n"
                f"- Purpose/Topic: {purpose}\n"
                f"- Tone: {tone}\n\n"
                "RULES:\n"
                "(1) Use ONLY the provided purpose; do not invent facts, amounts, or dates.\n"
                "(2) Greeting should be appropriate to the recipient.\n"
                "(3) Include a clear subject line.\n"
                "(4) The body must be complete — greeting, context, ask, next steps, "
                "and a professional sign-off. No placeholders like [Name].\n"
                "(5) Length: 100-250 words. Concise, actionable, respectful.\n"
                "(6) Do not claim the email was sent. Do not add unsubscribe links.\n"
                "(7) Return exactly ONE draft with `to` = the recipient email.\n"
            )

            bundle: EmailBundle = await llm.ainvoke([
                SystemMessage(content=system),
                HumanMessage(content=f"Original user request: {user_request}"),
            ])

            drafts = bundle.drafts or []
            if not drafts:
                return AgentOutput(
                    success=False,
                    error="LLM returned no drafts",
                )

            # Normalize the first draft
            first = drafts[0]
            draft_payload = {
                "to": recipient,
                "subject": first.subject,
                "body": first.body,
                "tone": first.tone or tone,
                "personalization_notes": first.personalization_notes,
            }

            return AgentOutput(
                success=True,
                result={
                    "requires_approval": True,
                    "action_kind": "email_send_single",
                    "draft": draft_payload,
                    "approval_reason": (
                        f"Send email to {recipient} — subject: {first.subject}"
                    ),
                },
            )

        except Exception as exc:
            return AgentOutput(success=False, error=f"email agent failed: {exc}")


__all__ = ["EmailAgent", "EmailBundle", "EmailDraft"]
