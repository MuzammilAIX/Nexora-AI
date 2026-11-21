"""
Approval routes — human-in-the-loop gate for sensitive agent actions.
"""
import asyncio
import sys
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..database.approval_models import Approval
from ..database.auth_models import User
from ..auth_deps import get_current_user
from ..agents.base import AgentInput
from ..agents.lead import LeadAgent
from ..agents.email import EmailAgent
from ..agents.research import ResearchAgent
from ..agents.reporting import ReportingAgent
from ..agents.review import ReviewAgent
from ..agents.support import SupportAgent
from ..audit import audit


router = APIRouter(prefix="/approvals", tags=["Approvals"])


def _ensure_windows_loop() -> None:
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except Exception:
            pass


_APPROVABLE_AGENTS = {
    "lead": LeadAgent,
    "email": EmailAgent,
    "research": ResearchAgent,
    "reporting": ReportingAgent,
    "review": ReviewAgent,
    "support": SupportAgent,
    # "operations": registered lazily below — we don't need the class to
    # execute an operations approval because the exact prepared action is
    # bound in proposed_action (Section 7.3). A sentinel None keeps the
    # agent_cls is None check from raising while still preventing accidental
    # agent re-execution here.
    "operations": None,
}


@router.get("")
async def list_approvals(
    status: str = "pending",
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(Approval)
        .where(Approval.tenant_id == user.tenant_id)
        .where(Approval.status == status)
        .order_by(Approval.created_at.desc())
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [
        {
            "id": str(r.id),
            "task_id": r.task_id,
            "agent_type": r.agent_type,
            "status": r.status,
            "reason": r.reason,
            "task_description": r.task_description,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/{approval_id}")
async def get_approval(
    approval_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(Approval)
        .where(Approval.id == approval_id)
        .where(Approval.tenant_id == user.tenant_id)
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    return {
        "id": str(row.id),
        "task_id": row.task_id,
        "agent_type": row.agent_type,
        "status": row.status,
        "reason": row.reason,
        "task_description": row.task_description,
        "proposed_action": row.proposed_action,
        "execution_result": row.execution_result,
        "created_at": row.created_at.isoformat(),
        "decided_at": row.decided_at.isoformat() if row.decided_at else None,
    }


@router.post("/{approval_id}/reject")
async def reject_approval(
    approval_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(Approval)
        .where(Approval.id == approval_id)
        .where(Approval.tenant_id == user.tenant_id)
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    if row.status != "pending":
        raise HTTPException(status_code=409, detail=f"Already {row.status}")

    from datetime import datetime, timezone
    row.status = "rejected"
    row.decided_by = user.id
    row.decided_at = datetime.now(timezone.utc)
    await session.commit()
    await audit(
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        event_type="approval.rejected",
        subject_type="approval",
        subject_id=str(row.id),
        run_id=str(row.run_id) if row.run_id else None,
        payload={
            "task_id": row.task_id,
            "agent_type": row.agent_type,
            "reason": row.reason,
        },
    )
    return {"id": str(row.id), "status": row.status}


@router.post("/{approval_id}/approve")
async def approve_approval(
    approval_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(Approval)
        .where(Approval.id == approval_id)
        .where(Approval.tenant_id == user.tenant_id)
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    if row.status != "pending":
        raise HTTPException(status_code=409, detail=f"Already {row.status}")

    # "operations" is intentionally registered as None: we don't re-run the
    # agent here — we execute the exact prepared action via action_kind
    # branches below (Section 7.3). All other agents still require a class.
    if row.agent_type not in _APPROVABLE_AGENTS:
        raise HTTPException(
            status_code=400,
            detail=f"No agent registered for '{row.agent_type}'",
        )
    agent_cls = _APPROVABLE_AGENTS.get(row.agent_type)


    _ensure_windows_loop()

    proposed = row.proposed_action or {}
    action_kind = proposed.get("action_kind") or "execute_agent"

    from datetime import datetime, timezone
    from ..tools.gmail import draft_reply, send_approved_draft

    # ------------------------------------------------------------
    # Execute the EXACT prepared action. Do NOT re-run the agent.
    # Section 7.3: "Approval must be bound to the exact action."
    # ------------------------------------------------------------
    execution = {"success": False, "result": {}, "error": None}

    if action_kind == "send_email" and row.agent_type == "support":
        thread_id = proposed.get("thread_id")
        body = proposed.get("response_draft")
        to_addr = proposed.get("to")
        if not thread_id or not body:
            execution["error"] = (
                "proposed_action is missing thread_id or response_draft; "
                "cannot execute approved send"
            )
        else:
            try:
                draft = await draft_reply(
                    tenant_id=str(row.tenant_id),
                    thread_id=thread_id,
                    body=body,
                )
                draft_id = (draft or {}).get("id") or (draft or {}).get("draft_id")
                if not draft_id:
                    execution["error"] = "Gmail draft creation returned no id"
                else:
                    sent = await send_approved_draft(
                        tenant_id=str(row.tenant_id),
                        draft_id=draft_id,
                    )
                    execution["success"] = True
                    execution["result"] = {
                        "action": "email_sent",
                        "to": to_addr,
                        "thread_id": thread_id,
                        "draft_id": draft_id,
                        "send_response": sent,
                    }
            except Exception as exc:
                execution["error"] = f"send failed: {exc}"
    elif action_kind == "send_email_generic" and row.agent_type == "operations":
        from ..tools.idempotency import (
            check_or_mark, mark_succeeded, mark_failed,
        )
        from ..tools.audit import log_event

        proposed_email = proposed.get("proposed_email") or {}
        to_addr = proposed_email.get("to")
        subject = proposed_email.get("subject")
        email_body = proposed_email.get("body")

        if not (to_addr and subject and email_body):
            execution["error"] = (
                "proposed_email is missing to/subject/body; "
                "cannot execute approved send"
            )
        else:
            idem_key = (
                f"email-approved:{row.tenant_id}:{to_addr}:"
                f"{subject}:{proposed.get('task_id', '')}"
            )
            is_fresh = await check_or_mark(
                idem_key, str(row.tenant_id), "send_email_approved"
            )
            if not is_fresh:
                execution["success"] = True
                execution["result"] = {
                    "action": "send_email",
                    "replayed": True,
                    "idempotency_key": idem_key,
                }
            else:
                try:
                    draft = await draft_reply(
                        tenant_id=str(row.tenant_id),
                        thread_id="",
                        body=(
                            f"To: {to_addr}\n"
                            f"Subject: {subject}\n\n"
                            f"{email_body}"
                        ),
                    )
                    draft_id = draft.get("id") or draft.get("draft_id")
                    if not draft_id:
                        raise RuntimeError("gmail draft creation returned no id")
                    sent = await send_approved_draft(
                        tenant_id=str(row.tenant_id),
                        draft_id=draft_id,
                    )
                    await mark_succeeded(idem_key, str(row.tenant_id))
                    await log_event(
                        tenant_id=str(row.tenant_id),
                        event_type="email.sent",
                        payload={
                            "to": to_addr,
                            "subject": subject,
                            "draft_id": draft_id,
                            "send_response": sent,
                        },
                        subject_type="workflow",
                        subject_id=draft_id,
                    )
                    execution["success"] = True
                    execution["result"] = {
                        "action": "send_email",
                        "to": to_addr,
                        "draft_id": draft_id,
                    }
                except Exception as exc:
                    await mark_failed(idem_key, str(row.tenant_id), str(exc))
                    execution["error"] = f"send_email failed: {exc}"
    elif action_kind == "create_order" and row.agent_type == "operations":
        from ..tools.operations_db import insert_order
        from ..tools.idempotency import (
            check_or_mark, mark_succeeded, mark_failed,
        )
        from ..tools.audit import log_event
        proposed_order = proposed.get("proposed_order") or {}
        customer_id = proposed_order.get("customer_id")
        items = proposed_order.get("items") or []
        total = proposed_order.get("total")

        if not customer_id or not items:
            execution["error"] = (
                "proposed_order is missing customer_id or items"
            )
        else:
            idem_key = (
                f"order-approved:{row.tenant_id}:{customer_id}:"
                f"{total}:{proposed.get('task_id', '')}"
            )
            is_fresh = await check_or_mark(
                idem_key, str(row.tenant_id), "create_order_approved"
            )
            if not is_fresh:
                execution["success"] = True
                execution["result"] = {
                    "action": "create_order",
                    "replayed": True,
                    "idempotency_key": idem_key,
                }
            else:
                try:
                    inserted = await insert_order(
                        tenant_id=str(row.tenant_id),
                        customer_id=customer_id,
                        items=items,
                        status="confirmed",
                    )
                    await mark_succeeded(idem_key, str(row.tenant_id))
                    await log_event(
                        tenant_id=str(row.tenant_id),
                        event_type="order.created_from_approval",
                        payload={
                            "order_id": inserted["order_id"],
                            "total": inserted["total"],
                            "approval_id": str(row.id),
                        },
                        subject_type="workflow",
                        subject_id=inserted["order_id"],
                    )
                    execution["success"] = True
                    execution["result"] = {
                        "action": "create_order",
                        "order_id": inserted["order_id"],
                        "total": inserted["total"],
                    }
                except Exception as exc:
                    await mark_failed(idem_key, str(row.tenant_id), str(exc))
                    execution["error"] = f"create_order failed: {exc}"
    else:
        execution["success"] = True
        execution["result"] = {
            "action": "noop",
            "note": f"agent_type '{row.agent_type}' has no executor yet",
        }

    if execution["success"]:
        row.status = "executed"
        row.decided_by = user.id
        row.decided_at = datetime.now(timezone.utc)
    else:
        row.status = "pending"

    row.execution_result = execution
    await session.commit()

    await audit(
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        event_type=(
            "approval.executed" if execution["success"]
            else "approval.execute_failed"
        ),
        subject_type="approval",
        subject_id=str(row.id),
        run_id=str(row.run_id) if row.run_id else None,
        payload={
            "task_id": row.task_id,
            "agent_type": row.agent_type,
            "action_kind": action_kind,
            "to": proposed.get("to"),
            "thread_id": proposed.get("thread_id"),
            "success": execution["success"],
            "error": execution["error"],
        },
    )

    if not execution["success"]:
        raise HTTPException(
            status_code=500,
            detail=f"Approval execution failed: {execution['error']}",
        )

    return {
        "id": str(row.id),
        "status": row.status,
        "execution_result": row.execution_result,
    }
