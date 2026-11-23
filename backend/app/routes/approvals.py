"""
Approval routes â€” human-in-the-loop gate for sensitive agent actions.
"""
import asyncio
import sys
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..database.approval_models import Approval
from ..database.auth_models import User
from ..auth_deps import get_current_user
from ..deps.permissions import require_permission
from ..agents.base import AgentInput
from ..agents.lead import LeadAgent
from ..agents.email import EmailAgent
from ..agents.research import ResearchAgent
from ..agents.reporting import ReportingAgent
from ..agents.sales import SalesAgent
from ..agents.review import ReviewAgent
from ..agents.support import SupportAgent
from ..audit import audit




class DecisionBody(BaseModel):
    note: str | None = None


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
    "sales": SalesAgent,
    "review": ReviewAgent,
    "support": SupportAgent,
    # "operations": registered lazily below â€” we don't need the class to
    # execute an operations approval because the exact prepared action is
    # bound in proposed_action (Section 7.3). A sentinel None keeps the
    # agent_cls is None check from raising while still preventing accidental
    # agent re-execution here.
    "operations": None,
    "calendar": None,   # handled by action_kind dispatch (calendar_create_event)
    "bulk_email": None,   # handled by action_kind dispatch (bulk_email_send)
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
            "decided_at": r.decided_at.isoformat() if r.decided_at else None,
            "decided_reason": r.decided_reason,
            "execution_result": r.execution_result or {},
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
        "decided_reason": row.decided_reason,
    }


@router.post("/{approval_id}/reject")
async def reject_approval(
    approval_id: UUID,
    body: DecisionBody = Body(default=DecisionBody()),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("approve_actions")),
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
    row.decided_reason = (body.note or '').strip() or None
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
    return {"id": str(row.id), "status": row.status, "decided_reason": row.decided_reason}


@router.post("/{approval_id}/approve")
async def approve_approval(
    approval_id: UUID,
    body: DecisionBody = Body(default=DecisionBody()),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("approve_actions")),
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
    # agent here â€” we execute the exact prepared action via action_kind
    # branches below (Section 7.3). All other agents still require a class.
    _agent_key = (row.agent_type or "").strip().lower()
    if _agent_key not in _APPROVABLE_AGENTS:
        raise HTTPException(
            status_code=400,
            detail=f"No agent registered for '{row.agent_type}'",
        )
    agent_cls = _APPROVABLE_AGENTS.get(_agent_key)


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
        # Support can put fields at top level OR inside prepared_result;
        # accept either shape.
        prepared = proposed.get("prepared_result") or {}
        proposed_email = proposed.get("proposed_email") or prepared.get("proposed_email") or {}
        thread_id = (
            proposed.get("thread_id")
            or prepared.get("thread_id")
            or proposed_email.get("thread_id")
        )
        body = (
            proposed.get("response_draft")
            or prepared.get("response_draft")
            or proposed_email.get("body")
        )
        to_addr = (
            proposed.get("to")
            or prepared.get("to")
            or proposed_email.get("to")
        )
        if not thread_id or not body:
            execution["error"] = (
                "proposed_action is missing thread_id or response_draft; "
                "cannot execute approved send"
            )
        else:
            try:
                # draft_reply expects a formatted "To: X\nSubject: Y\n\nbody"
                # string. The support agent provides just the body text, so
                # reconstruct the headers here.
                subj = (
                    proposed.get("subject")
                    or proposed_email.get("subject")
                    or "Re: your message"
                )
                to_for_header = to_addr or "customer"
                formatted_body = (
                    f"To: {to_for_header}\n"
                    f"Subject: {subj}\n\n"
                    f"{body}"
                )
                draft = await draft_reply(
                    tenant_id=str(row.tenant_id),
                    thread_id=thread_id,
                    body=formatted_body,
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
    elif action_kind == "email_send_single" and row.agent_type == "email":
        from ..tools.gmail import send_approved_draft, draft_reply
        from ..tools.audit import log_event

        prepared = proposed.get("proposed_action") or proposed.get("prepared_result") or {}
        draft = prepared.get("draft") or proposed.get("draft") or {}
        to_addr = draft.get("to")
        subject = draft.get("subject", "")
        body = draft.get("body", "")

        if not to_addr or not body:
            execution["error"] = "email_send_single: missing recipient or body"
        else:
            try:
                formatted = f"To: {to_addr}\nSubject: {subject}\n\n{body}"
                draft_result = await draft_reply(
                    tenant_id=str(row.tenant_id),
                    thread_id="",
                    body=formatted,
                )
                draft_id = (draft_result or {}).get("id") or (draft_result or {}).get("draft_id")
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
                        "subject": subject,
                        "message_id": (sent or {}).get("id"),
                    }
                    await log_event(
                        tenant_id=str(row.tenant_id),
                        event_type="email.sent_from_approval",
                        payload={"to": to_addr, "subject": subject, "approval_id": str(row.id)},
                        subject_type="workflow",
                        subject_id=str(row.id),
                    )
            except Exception as exc:
                execution["error"] = f"email_send_single failed: {exc}"

    elif action_kind == "bulk_email_send" and row.agent_type == "bulk_email":
        from ..tools.bulk_email import send_campaign
        from ..tools.audit import log_event

        prepared = proposed.get("proposed_action") or proposed.get("prepared_result") or {}
        campaign = prepared.get("campaign_preview") or proposed.get("campaign_preview") or []
        test_recipient = prepared.get("test_recipient") or proposed.get("test_recipient")

        if not campaign:
            execution["error"] = "campaign_preview is empty"
        else:
            try:
                result = await send_campaign(
                    tenant_id=str(row.tenant_id),
                    campaign=campaign,
                    test_recipient=test_recipient,
                )
                execution["success"] = (result["failed"] == 0)
                execution["result"] = result
                await log_event(
                    tenant_id=str(row.tenant_id),
                    event_type="bulk_email.sent",
                    payload={
                        "sent": result["sent"],
                        "failed": result["failed"],
                        "test_mode": bool(test_recipient),
                        "approval_id": str(row.id),
                    },
                    subject_type="workflow",
                    subject_id=str(row.id),
                )
            except Exception as exc:
                execution["error"] = f"bulk_email_send failed: {exc}"

    elif action_kind == "calendar_create_event" and row.agent_type == "calendar":
        from ..tools.calendar import create_event
        from ..tools.audit import log_event

        prepared = proposed.get("proposed_action") or proposed.get("prepared_result") or {}
        summary = proposed.get("summary") or prepared.get("summary") or "Meeting"
        start_iso = proposed.get("start_iso") or prepared.get("start_iso", "")
        end_iso = proposed.get("end_iso") or prepared.get("end_iso", "")
        attendees = proposed.get("attendees") or prepared.get("attendees") or []
        description = proposed.get("description") or prepared.get("description", "")

        if not start_iso or not end_iso:
            execution["error"] = "proposed_action missing start_iso/end_iso"
        else:
            try:
                ev = await create_event(
                    tenant_id=str(row.tenant_id),
                    summary=summary,
                    start_iso=start_iso,
                    end_iso=end_iso,
                    attendees=attendees,
                    description=description,
                )
                await log_event(
                    tenant_id=str(row.tenant_id),
                    event_type="calendar.event_created_from_approval",
                    payload={
                        "event_id": ev.get("id"),
                        "summary": summary,
                        "approval_id": str(row.id),
                    },
                    subject_type="workflow",
                    subject_id=ev.get("id"),
                )
                execution["success"] = True
                execution["result"] = {
                    "action": "create_event",
                    "event_id": ev.get("id"),
                    "html_link": ev.get("htmlLink"),
                    "summary": summary,
                }
            except Exception as exc:
                execution["error"] = f"calendar create_event failed: {exc}"

    elif action_kind == "execute_agent" and row.agent_type == "lead":
        from ..tools.crm import create_task
        from ..tools.audit import log_event

        prepared = proposed.get("prepared_result") or {}
        scored_leads = prepared.get("scored_leads") or []
        high_value = [l for l in scored_leads
                      if (l.get("score") or 0) >= 70]

        if not high_value:
            execution["success"] = True
            execution["result"] = {
                "action": "score_leads",
                "scored_leads": len(scored_leads),
                "tasks_created": [],
                "note": "no leads scored >= 70; no tasks created",
            }
        else:
            tasks_created: list[str] = []
            errors: list[dict] = []
            for lead in high_value:
                try:
                    task = await create_task(
                        tenant_id=str(row.tenant_id),
                        subject=lead.get("follow_up_subject")
                            or f"Follow up with {lead.get('name', 'lead')}",
                        body=lead.get("follow_up_body") or "",
                        contact_id=lead.get("contact_id"),
                        due_at=None,
                    )
                    task_id = (task or {}).get("id")
                    if task_id:
                        tasks_created.append(task_id)
                    else:
                        errors.append({
                            "contact_id": lead.get("contact_id"),
                            "error": "create_task returned no id",
                            "response": task,
                        })
                except Exception as exc:
                    errors.append({
                        "contact_id": lead.get("contact_id"),
                        "error": f"{type(exc).__name__}: {exc}",
                    })

            await log_event(
                tenant_id=str(row.tenant_id),
                event_type="crm.tasks.created",
                payload={
                    "approval_id": str(row.id),
                    "tasks_created": tasks_created,
                    "errors": errors,
                    "leads_processed": len(high_value),
                },
                subject_type="workflow",
                subject_id=str(row.id),
            )

            execution["success"] = len(tasks_created) > 0 or len(errors) == 0
            execution["result"] = {
                "action": "create_lead_tasks",
                "scored_leads": len(scored_leads),
                "tasks_created": tasks_created,
                "errors": errors,
            }
            if not execution["success"]:
                execution["error"] = f"{len(errors)} task(s) failed"

    elif action_kind == "execute_agent" and row.agent_type == "reporting":
        from ..tools.audit import log_event
        prepared = proposed.get("prepared_result") or {}
        report_content = (
            prepared.get("report")
            or prepared.get("report_markdown")
            or prepared.get("content")
            or prepared.get("summary")
        )
        report_title = (
            prepared.get("title")
            or prepared.get("report_title")
            or "Sales Report"
        )
        await log_event(
            tenant_id=str(row.tenant_id),
            event_type="reporting.report.approved",
            payload={"approval_id": str(row.id), "title": report_title},
            subject_type="workflow",
            subject_id=str(row.id),
        )
        execution["success"] = True
        execution["result"] = {
            "action": "accept_report",
            "title": report_title,
            "report": report_content,
            "note": "Report approved by human reviewer.",
        }
    elif action_kind == "execute_agent" and row.agent_type == "research":
        from ..tools.audit import log_event
        prepared = proposed.get("prepared_result") or {}
        execution["success"] = True
        execution["result"] = {
            "action": "accept_research",
            "findings": prepared.get("findings") or prepared.get("summary"),
            "note": "Research accepted by human reviewer.",
        }
        await log_event(
            tenant_id=str(row.tenant_id),
            event_type="research.accepted",
            payload={"approval_id": str(row.id)},
            subject_type="workflow",
            subject_id=str(row.id),
        )
    elif action_kind == "execute_agent" and row.agent_type == "review":
        from ..tools.audit import log_event
        prepared = proposed.get("prepared_result") or {}
        execution["success"] = True
        execution["result"] = {
            "action": "accept_review",
            "review": prepared.get("review") or prepared.get("summary"),
            "note": "Review accepted by human reviewer.",
        }
        await log_event(
            tenant_id=str(row.tenant_id),
            event_type="review.accepted",
            payload={"approval_id": str(row.id)},
            subject_type="workflow",
            subject_id=str(row.id),
        )
    else:
        # No registered executor for this agent/action combo. Record the
        # human decision anyway so the row does not stay stuck as pending.
        execution["success"] = True
        execution["result"] = {
            "action": "manual_approval_no_executor",
            "note": (
                f"No automated executor for agent_type='{row.agent_type}' "
                f"action_kind='{action_kind}'. Approval recorded manually."
            ),
            "agent_type": row.agent_type,
            "action_kind": action_kind,
        }
    if execution["success"]:
        row.status = "executed"
        row.decided_by = user.id
        row.decided_at = datetime.now(timezone.utc)
    else:
        row.status = "pending"

    row.decided_reason = (body.note or '').strip() or None
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
        "decided_reason": row.decided_reason, "execution_result": row.execution_result,
    }
