"""
Operations Agent — inventory, orders, customers.

Capabilities:
  - query_products  (read)
  - query_orders    (read)
  - reorder         (write, idempotent, approval if total > $500)
  - flag_customer   (write, idempotent)
  - send_email      (external, idempotent + retry)

Respects context["prepare_only"]:
  True  -> return proposed action, no DB write
  False -> execute (insert order / update segment / send email)
"""
from datetime import date
from typing import Any, Literal

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, ConfigDict, Field

from .base import BaseAgent, AgentInput, AgentOutput
from ..config import settings
from ..tools.audit import log_event
from ..tools.idempotency import check_or_mark, mark_succeeded, mark_failed
from ..tools.retry import with_retry
from ..tools.operations_db import (
    list_products,
    get_product_by_name,
    get_customer_by_email,
    list_orders,
    insert_order,
    update_customer_segment,
)


APPROVAL_THRESHOLD = 500.0


class OperationsPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal[
        "query_products",
        "query_orders",
        "reorder",
        "flag_customer",
        "send_email",
    ]
    product_name: str | None = None
    category: str | None = None
    customer_email: str | None = None
    quantity: int | None = None
    segment: str | None = None
    status_filter: str | None = None
    email_subject: str | None = None
    email_body: str | None = None
    reasoning: str = Field(description="One sentence on why this action")


_SYSTEM_PROMPT = (
    "You are Nexora AI's Operations Agent. Classify the user's request "
    "into exactly one action from the OperationsPlan schema. Do not "
    "invent product names or customer emails — extract them from the "
    "user's text verbatim. If a required field is missing, set it to "
    "null. Actions:\n"
    "- query_products: list/inspect inventory (product_name, category)\n"
    "- query_orders: list orders (status_filter)\n"
    "- reorder: create an order (product_name, quantity, customer_email)\n"
    "- flag_customer: update customer segment (customer_email, segment)\n"
    "- send_email: send an email (customer_email, email_subject, email_body)\n"
)


class OperationsAgent(BaseAgent):
    name = "operations"

    async def run(self, payload: AgentInput) -> AgentOutput:
        try:
            ctx = payload.context or {}
            tenant_id = ctx.get("tenant_id")
            user_request = ctx.get("user_request") or payload.task_description
            prepare_only = bool(ctx.get("prepare_only", False))

            if not tenant_id:
                return AgentOutput(
                    success=False, error="operations agent requires tenant_id"
                )

            # 1. Plan
            llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY,
                timeout=60,
                max_retries=2,
            ).with_structured_output(OperationsPlan)

            plan: OperationsPlan = await llm.ainvoke([
                SystemMessage(content=_SYSTEM_PROMPT),
                HumanMessage(content=user_request),
            ])

            # 2. Dispatch
            if plan.action == "query_products":
                return await self._query_products(tenant_id, plan)
            if plan.action == "query_orders":
                return await self._query_orders(tenant_id, plan)
            if plan.action == "reorder":
                return await self._reorder(tenant_id, plan, prepare_only)
            if plan.action == "flag_customer":
                return await self._flag_customer(tenant_id, plan, prepare_only)
            if plan.action == "send_email":
                return await self._send_email(tenant_id, plan, prepare_only)

            return AgentOutput(success=False, error=f"unknown action {plan.action}")

        except Exception as exc:
            return AgentOutput(success=False, error=str(exc))

    # ---------------- reads ----------------

    async def _query_products(
        self, tenant_id: str, plan: OperationsPlan,
    ) -> AgentOutput:
        products = await list_products(
            tenant_id=tenant_id,
            name_filter=plan.product_name,
            category=plan.category,
        )
        await log_event(
            tenant_id=tenant_id,
            event_type="operations.query_products",
            payload={"count": len(products), "filter": plan.product_name},
            subject_type="workflow",
            subject_id=f"products:{plan.product_name or '*'}",
        )
        return AgentOutput(
            success=True,
            result={"action": "query_products", "products": products},
        )

    async def _query_orders(
        self, tenant_id: str, plan: OperationsPlan,
    ) -> AgentOutput:
        orders = await list_orders(
            tenant_id=tenant_id,
            status=plan.status_filter,
        )
        await log_event(
            tenant_id=tenant_id,
            event_type="operations.query_orders",
            payload={"count": len(orders), "status": plan.status_filter},
            subject_type="workflow",
            subject_id=f"orders:{plan.status_filter or '*'}",
        )
        return AgentOutput(
            success=True,
            result={"action": "query_orders", "orders": orders},
        )

    # ---------------- writes ----------------

    async def _reorder(
        self,
        tenant_id: str,
        plan: OperationsPlan,
        prepare_only: bool,
    ) -> AgentOutput:
        if not (plan.product_name and plan.quantity and plan.customer_email):
            return AgentOutput(
                success=False,
                error="reorder requires product_name, quantity, customer_email",
            )

        product = await get_product_by_name(tenant_id, plan.product_name)
        if product is None:
            return AgentOutput(
                success=False, error=f"product '{plan.product_name}' not found",
            )

        customer = await get_customer_by_email(tenant_id, plan.customer_email)
        if customer is None:
            return AgentOutput(
                success=False,
                error=f"customer '{plan.customer_email}' not found",
            )

        item = {
            "product_id": product["id"],
            "quantity": plan.quantity,
            "unit_price": product["unit_price"],
        }
        total = round(plan.quantity * product["unit_price"], 2)
        needs_approval = total > APPROVAL_THRESHOLD

        # Prepare phase: return proposed action, no DB write.
        if prepare_only:
            return AgentOutput(
                success=True,
                result={
                    "action": "reorder_prepared",
                    "proposed_order": {
                        "customer_id": customer["id"],
                        "customer_email": customer["email"],
                        "items": [item],
                        "total": total,
                    },
                    "action_kind": "create_order",
                    "requires_approval": needs_approval,
                    "approval_reason": (
                        f"Order total ${total:.2f} exceeds "
                        f"${APPROVAL_THRESHOLD:.0f} threshold"
                        if needs_approval else None
                    ),
                },
            )

        # Execute phase: idempotency-gated insert.
        idem_key = (
            f"order:{tenant_id}:{customer['id']}:"
            f"{product['id']}:{plan.quantity}:{date.today().isoformat()}"
        )
        is_fresh = await check_or_mark(idem_key, tenant_id, "create_order")
        if not is_fresh:
            return AgentOutput(
                success=True,
                result={
                    "action": "reorder",
                    "replayed": True,
                    "idempotency_key": idem_key,
                },
            )

        try:
            inserted = await insert_order(
                tenant_id=tenant_id,
                customer_id=customer["id"],
                items=[item],
                status="confirmed",
            )
            await mark_succeeded(idem_key, tenant_id)
            await log_event(
                tenant_id=tenant_id,
                event_type="order.created",
                payload={
                    "order_id": inserted["order_id"],
                    "total": inserted["total"],
                    "customer_email": customer["email"],
                    "product_name": product["name"],
                    "quantity": plan.quantity,
                },
                subject_type="workflow",
                subject_id=inserted["order_id"],
            )
            return AgentOutput(
                success=True,
                result={
                    "action": "reorder",
                    "order_id": inserted["order_id"],
                    "total": inserted["total"],
                    "idempotency_key": idem_key,
                },
            )
        except Exception as exc:
            await mark_failed(idem_key, tenant_id, str(exc))
            raise

    async def _flag_customer(
        self,
        tenant_id: str,
        plan: OperationsPlan,
        prepare_only: bool,
    ) -> AgentOutput:
        if not (plan.customer_email and plan.segment):
            return AgentOutput(
                success=False,
                error="flag_customer requires customer_email and segment",
            )

        customer = await get_customer_by_email(tenant_id, plan.customer_email)
        if customer is None:
            return AgentOutput(
                success=False,
                error=f"customer '{plan.customer_email}' not found",
            )

        if prepare_only:
            return AgentOutput(
                success=True,
                result={
                    "action": "flag_customer_prepared",
                    "proposed_flag": {
                        "customer_id": customer["id"],
                        "customer_email": customer["email"],
                        "current_segment": customer["segment"],
                        "new_segment": plan.segment,
                    },
                    "action_kind": "flag_customer",
                    "requires_approval": False,
                },
            )

        idem_key = f"flag:{tenant_id}:{customer['id']}:{plan.segment}"
        is_fresh = await check_or_mark(idem_key, tenant_id, "flag_customer")
        if not is_fresh:
            return AgentOutput(
                success=True,
                result={
                    "action": "flag_customer",
                    "replayed": True,
                    "idempotency_key": idem_key,
                },
            )
        try:
            ok = await update_customer_segment(
                tenant_id, customer["id"], plan.segment,
            )
            await mark_succeeded(idem_key, tenant_id)
            await log_event(
                tenant_id=tenant_id,
                event_type="customer.flagged",
                payload={
                    "customer_id": customer["id"],
                    "customer_email": customer["email"],
                    "previous_segment": customer["segment"],
                    "new_segment": plan.segment,
                    "updated": ok,
                },
                subject_type="workflow",
                subject_id=customer["id"],
            )
            return AgentOutput(
                success=True,
                result={
                    "action": "flag_customer",
                    "customer_id": customer["id"],
                    "new_segment": plan.segment,
                },
            )
        except Exception as exc:
            await mark_failed(idem_key, tenant_id, str(exc))
            raise

    async def _send_email(
        self,
        tenant_id: str,
        plan: OperationsPlan,
        prepare_only: bool,
    ) -> AgentOutput:
        if not (plan.customer_email and plan.email_subject and plan.email_body):
            return AgentOutput(
                success=False,
                error="send_email requires customer_email, email_subject, email_body",
            )

        if prepare_only:
            return AgentOutput(
                success=True,
                result={
                    "action": "send_email_prepared",
                    "proposed_email": {
                        "to": plan.customer_email,
                        "subject": plan.email_subject,
                        "body": plan.email_body,
                    },
                    "action_kind": "send_email_generic",
                    "requires_approval": True,
                    "approval_reason": "External email requires human approval",
                },
            )

        idem_key = (
            f"email:{tenant_id}:{plan.customer_email}:"
            f"{plan.email_subject}:{date.today().isoformat()}"
        )
        is_fresh = await check_or_mark(idem_key, tenant_id, "send_email")
        if not is_fresh:
            return AgentOutput(
                success=True,
                result={
                    "action": "send_email",
                    "replayed": True,
                    "idempotency_key": idem_key,
                },
            )
        try:
            from ..tools.gmail import (
                draft_reply as _draft,
                send_approved_draft as _send,
            )
            # Generic email: draft a new message, send it immediately
            # (approval already happened upstream if prepare_only was used).
            draft = await with_retry(
                _draft,
                tenant_id=tenant_id,
                thread_id="",   # new thread
                body=(
                    f"To: {plan.customer_email}\n"
                    f"Subject: {plan.email_subject}\n\n"
                    f"{plan.email_body}"
                ),
                max_attempts=3,
                operation="gmail.draft_reply",
            )
            draft_id = (draft or {}).get("id") or (draft or {}).get("draft_id")
            if not draft_id:
                raise RuntimeError("gmail draft creation returned no id")
            sent = await with_retry(
                _send,
                tenant_id=tenant_id,
                draft_id=draft_id,
                max_attempts=3,
                operation="gmail.send_approved_draft",
            )
            await mark_succeeded(idem_key, tenant_id)
            await log_event(
                tenant_id=tenant_id,
                event_type="email.sent",
                payload={
                    "to": plan.customer_email,
                    "subject": plan.email_subject,
                    "draft_id": draft_id,
                    "send_response": sent,
                },
                subject_type="workflow",
                subject_id=draft_id,
            )
            return AgentOutput(
                success=True,
                result={
                    "action": "send_email",
                    "to": plan.customer_email,
                    "draft_id": draft_id,
                },
            )
        except Exception as exc:
            await mark_failed(idem_key, tenant_id, str(exc))
            raise
