"""
Customer Support Agent.

Loads a support email from Gmail, classifies the issue, looks up customer context,
retrieves relevant KB articles, and drafts a response.

The draft response requires approval before sending (per business doc Section 7.3:
"Send external emails: Approval by default for initial release").
"""
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, ConfigDict, Field
import json as _json

from .base import BaseAgent, AgentInput, AgentOutput
from ..config import settings
from ..tools.gmail import (
    search_emails,
    get_email,
    format_email,
    format_emails,
)
from ..tools.tickets import (
    lookup_customer,
    search_knowledge,
    format_customer,
    format_knowledge,
)


class TicketClassification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str = Field(
        description="One of: billing, access, technical, complaint, other"
    )
    priority: str = Field(
        description="One of: low, medium, high, urgent"
    )
    needed_info: list[str] = Field(
        description="Specific info needed from the customer or system to resolve"
    )


class SupportDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_draft: str = Field(
        description="Customer-facing response, grounded ONLY in email/customer/KB data"
    )
    evidence_used: list[str] = Field(
        description="KB entry ids and data fields cited (e.g. 'kb-001', 'customer.plan')"
    )
    confidence: int = Field(
        description="0-100 confidence that this draft correctly resolves the issue"
    )
    escalation_reason: str = Field(
        description="If escalation is needed, why. Empty string otherwise."
    )


class SupportFindings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(description="One-line summary of what was done")
    email_id: str = Field(description="Email id this resolution addresses")
    thread_id: str = Field(description="Thread id for the reply")
    classification: TicketClassification
    draft: SupportDraft
    gaps: list[str] = Field(
        description="What could not be determined from available data"
    )


def _build_system_prompt() -> str:
    return (
        "You are Nexora AI's customer support specialist. "
        "You handle incoming support emails end-to-end: classify the issue, "
        "look up the customer, retrieve relevant knowledge, and draft a "
        "grounded response.\n\n"
        "RULES:\n"
        "(1) Use ONLY the data provided in the email, customer record, and "
        "knowledge base. Do not invent facts, policies, refund amounts, or "
        "timelines.\n"
        "(2) If the customer record is missing or the KB has no matching "
        "entry, say so in `gaps` and set confidence lower.\n"
        "(3) For billing issues involving refunds, be specific about the exact "
        "amount and customer in the draft.\n"
        "(4) For urgent issues (outages, security, data loss), set "
        "escalation_reason and do NOT attempt self-service resolution.\n"
        "(5) The response draft must be professional, empathetic, and "
        "specific to THIS customer's actual situation.\n"
        "(6) Always cite which KB entries and customer fields you used in "
        "`evidence_used`.\n"
        "(7) The email_id and thread_id MUST match the values from the "
        "input email - do not invent new ones."
    )


def _build_prompt(
    payload: AgentInput,
    email_block: str,
    customer_block: str,
    knowledge_block: str,
    email_metadata: dict,
) -> str:
    context = payload.context or {}
    deps = context.get("dependency_outputs") or {}
    prior = ""
    if deps:
        prior = (
            "\n\nPRIOR TASK OUTPUTS (build on these):\n"
            f"{_json.dumps(deps, indent=2, default=str)[:2000]}"
        )
    return (
        f"Task: {payload.task_description}\n\n"
        f"EMAIL METADATA:\n"
        f"- email_id: {email_metadata.get('id')}\n"
        f"- thread_id: {email_metadata.get('threadId')}\n"
        f"- from: {email_metadata.get('from')}\n\n"
        f"EMAIL CONTENT:\n{email_block}\n\n"
        f"CUSTOMER RECORD:\n{customer_block}\n\n"
        f"KNOWLEDGE BASE MATCHES:\n{knowledge_block}\n\n"
        f"Produce a complete resolution for this email."
        f"{prior}"
    )


class SupportAgent(BaseAgent):
    name = "support"

    async def run(self, payload: AgentInput) -> AgentOutput:
        try:
            context = payload.context or {}
            tenant_id = context.get("tenant_id")
            email_id = context.get("email_id") or ""

            # 1. Load the email (deterministic)
            if email_id:
                email = await get_email(tenant_id=tenant_id, message_id=email_id)
            else:
                # No email_id - pick the highest-priority unread email
                unread = await search_emails(tenant_id=tenant_id, limit=10)
                email = unread[0] if unread else None

            if not email:
                return AgentOutput(
                    success=False,
                    error="No email found to process",
                )

            email_block = format_email(email)
            thread_id = email.get("threadId", "")

            # 2. Look up customer (deterministic)
            customer = await lookup_customer(
                tenant_id=tenant_id,
                email=email.get("from"),
            )
            customer_block = format_customer(customer)

            # 3. Retrieve knowledge (deterministic)
            kb_query = f"{email.get('subject','')} {email.get('body','')}"
            knowledge = await search_knowledge(
                tenant_id=tenant_id,
                query=kb_query,
                limit=5,
            )
            knowledge_block = format_knowledge(knowledge)

            # 4. Classify + draft via LLM with structured output
            llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY,
                timeout=90,
                max_retries=2,
            ).with_structured_output(SupportFindings)

            findings = await llm.ainvoke([
                SystemMessage(content=_build_system_prompt()),
                HumanMessage(content=_build_prompt(
                    payload,
                    email_block,
                    customer_block,
                    knowledge_block,
                    {
                        "id": email.get("id"),
                        "threadId": thread_id,
                        "from": email.get("from"),
                    },
                )),
            ])

            # 5. Return structured result
            result = findings.model_dump()
            result["email"] = email
            result["customer"] = customer
            result["knowledge_ids"] = [k.get("id") for k in knowledge]
            result["email_id"] = email.get("id")
            result["thread_id"] = thread_id
            result["needs_send_approval"] = True
            result["approval_reason"] = (
                f"Response to {email.get('from')} requires human approval "
                "before sending (external email policy)."
            )
            return AgentOutput(success=True, result=result)

        except Exception as exc:
            return AgentOutput(success=False, error=str(exc))
