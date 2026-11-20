"""
Ticket / customer / knowledge tools for the Support Agent.

SLICE 1: Mock data for development and testing.
SLICE 2: Replace with Gmail + real helpdesk integration.

Follows the same shape as crm.py: async functions, tenant_id first,
plain dicts returned, format_* helpers for prompt rendering.
"""
import asyncio
import sys
from typing import Any


def _ensure_windows_loop_policy() -> None:
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(
                asyncio.WindowsSelectorEventLoopPolicy()
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# MOCK DATA - replaced in Slice 2 with real Gmail/helpdesk
# ---------------------------------------------------------------------------
_MOCK_TICKETS: dict[str, list[dict[str, Any]]] = {
    # Example tenant bucket - used when no tenant-specific data exists
    "_default": [
        {
            "id": "ticket-001",
            "subject": "Cannot access premium features",
            "body": (
                "Hi, I purchased your premium subscription yesterday "
                "but I still cannot access the premium features in my "
                "account. I tried logging out and back in. Please help. "
                "My account email is sarah@acmecorp.com"
            ),
            "from_email": "sarah@acmecorp.com",
            "customer_name": "Sarah Chen",
            "status": "open",
            "priority": "high",
            "created_at": "2026-11-20T09:15:00Z",
        },
        {
            "id": "ticket-002",
            "subject": "Billing question about my invoice",
            "body": (
                "I was charged twice this month for the same subscription. "
                "Could you check my account and refund the duplicate charge? "
                "Order number is INV-2026-11-1847."
            ),
            "from_email": "mike@talltree.io",
            "customer_name": "Mike Rodriguez",
            "status": "open",
            "priority": "medium",
            "created_at": "2026-11-20T10:22:00Z",
        },
        {
            "id": "ticket-003",
            "subject": "API integration error 401",
            "body": (
                "Our integration with your API is failing with 401 errors "
                "starting this morning. We use the same API key as before "
                "and it was working yesterday. Account: techwave.dev"
            ),
            "from_email": "ops@techwave.dev",
            "customer_name": "TechWave Operations",
            "status": "open",
            "priority": "urgent",
            "created_at": "2026-11-20T08:45:00Z",
        },
    ]
}

_MOCK_CUSTOMERS: dict[str, dict[str, Any]] = {
    "sarah@acmecorp.com": {
        "id": "cust-1001",
        "name": "Sarah Chen",
        "email": "sarah@acmecorp.com",
        "company": "Acme Corp",
        "plan": "premium",
        "status": "active",
        "subscription_started": "2026-11-19T14:30:00Z",
        "notes": "Trial converted to premium yesterday.",
    },
    "mike@talltree.io": {
        "id": "cust-1002",
        "name": "Mike Rodriguez",
        "email": "mike@talltree.io",
        "company": "Tall Tree Consulting",
        "plan": "premium",
        "status": "active",
        "subscription_started": "2026-06-01T00:00:00Z",
        "notes": "Long-term customer, no prior billing issues.",
    },
    "ops@techwave.dev": {
        "id": "cust-1003",
        "name": "TechWave Operations",
        "email": "ops@techwave.dev",
        "company": "TechWave",
        "plan": "enterprise",
        "status": "active",
        "subscription_started": "2025-03-15T00:00:00Z",
        "notes": "Enterprise account. API key rotation was scheduled for this week.",
    },
}

_MOCK_KB: list[dict[str, Any]] = [
    {
        "id": "kb-001",
        "title": "Premium features not accessible after purchase",
        "content": (
            "If a customer purchased premium but cannot access features: "
            "(1) Verify the subscription status in the billing system. "
            "(2) Check if the account has been re-provisioned after payment. "
            "(3) Ask the customer to log out, clear cookies, and log in again. "
            "(4) If still failing, manually trigger account refresh from admin. "
            "Most cases resolve within 15 minutes of payment confirmation."
        ),
        "tags": ["access", "premium", "billing", "provisioning"],
    },
    {
        "id": "kb-002",
        "title": "Handling duplicate billing charges",
        "content": (
            "Duplicate charges usually occur when payment retries succeed "
            "after a timeout. Steps: "
            "(1) Look up the invoice by order number. "
            "(2) Verify both charges cleared. "
            "(3) Issue refund for the duplicate within 3 business days. "
            "(4) Reply with refund confirmation and expected timeline "
            "(5-7 business days to appear on statement)."
        ),
        "tags": ["billing", "refund", "duplicate", "invoice"],
    },
    {
        "id": "kb-003",
        "title": "API 401 errors after key rotation",
        "content": (
            "401 errors starting suddenly often mean the API key was rotated. "
            "Steps: "
            "(1) Confirm whether the account has a scheduled key rotation. "
            "(2) Check if the old key was invalidated. "
            "(3) Provide the new key via the secure dashboard. "
            "(4) Explain to the customer that key rotation is a security "
            "best practice and provide the exact cutover timestamp."
        ),
        "tags": ["api", "authentication", "401", "key-rotation"],
    },
    {
        "id": "kb-004",
        "title": "Escalation policy for urgent tickets",
        "content": (
            "Urgent tickets include: service outages, security incidents, "
            "and data loss. For these, immediately escalate to on-call "
            "engineering and set priority to urgent. Do not attempt "
            "self-service resolution without engineering involvement."
        ),
        "tags": ["escalation", "urgent", "policy"],
    },
]


# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------
async def search_tickets(
    tenant_id: str | None = None,
    query: str = "",
    status: str = "open",
    limit: int = 20,
) -> list[dict[str, Any]]:
    _ensure_windows_loop_policy()
    tickets = _MOCK_TICKETS.get("_default", [])
    if status:
        tickets = [t for t in tickets if t.get("status") == status]
    if query:
        q = query.lower()
        tickets = [
            t for t in tickets
            if q in t.get("subject", "").lower()
            or q in t.get("body", "").lower()
        ]
    return tickets[:limit]


async def get_ticket(
    tenant_id: str | None = None,
    ticket_id: str = "",
) -> dict[str, Any] | None:
    _ensure_windows_loop_policy()
    for t in _MOCK_TICKETS.get("_default", []):
        if t.get("id") == ticket_id:
            return t
    return None


async def lookup_customer(
    tenant_id: str | None = None,
    email: str | None = None,
    customer_id: str | None = None,
) -> dict[str, Any] | None:
    _ensure_windows_loop_policy()
    if email:
        return _MOCK_CUSTOMERS.get(email.lower())
    if customer_id:
        for c in _MOCK_CUSTOMERS.values():
            if c.get("id") == customer_id:
                return c
    return None


async def search_knowledge(
    tenant_id: str | None = None,
    query: str = "",
    limit: int = 5,
) -> list[dict[str, Any]]:
    _ensure_windows_loop_policy()
    if not query:
        return _MOCK_KB[:limit]
    q = query.lower()
    # Naive keyword scoring for now - slice 2 can use embeddings
    scored: list[tuple[int, dict[str, Any]]] = []
    for entry in _MOCK_KB:
        score = 0
        for tag in entry.get("tags", []):
            if tag.lower() in q:
                score += 3
        if entry["title"].lower().find(q.split()[0] if q else "") != -1:
            score += 2
        if any(w in entry["content"].lower() for w in q.split() if len(w) > 3):
            score += 1
        if score > 0:
            scored.append((score, entry))
    scored.sort(key=lambda x: -x[0])
    return [entry for _, entry in scored[:limit]]


def format_tickets(tickets: list[dict[str, Any]]) -> str:
    if not tickets:
        return "(no tickets)"
    lines = []
    for t in tickets:
        lines.append(
            f"- id={t.get('id')} | from={t.get('from_email')} | "
            f"subject={t.get('subject')} | priority={t.get('priority')} | "
            f"status={t.get('status')}"
        )
    return "\n".join(lines)


def format_customer(customer: dict[str, Any] | None) -> str:
    if not customer:
        return "(no customer record)"
    return (
        f"id={customer.get('id')} | name={customer.get('name')} | "
        f"email={customer.get('email')} | company={customer.get('company')} | "
        f"plan={customer.get('plan')} | status={customer.get('status')} | "
        f"notes={customer.get('notes','')}"
    )


def format_knowledge(entries: list[dict[str, Any]]) -> str:
    if not entries:
        return "(no knowledge base entries)"
    lines = []
    for e in entries:
        lines.append(
            f"--- {e.get('id')}: {e.get('title')} ---\n{e.get('content')}"
        )
    return "\n\n".join(lines)
