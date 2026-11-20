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

    agent_cls = _APPROVABLE_AGENTS.get(row.agent_type)
    if agent_cls is None:
        raise HTTPException(
            status_code=400,
            detail=f"No agent registered for '{row.agent_type}'",
        )

    _ensure_windows_loop()

    proposed = row.proposed_action or {}
    context = dict(proposed.get("context_preview") or {})
    context["create_tasks"] = True
    context["approved_by"] = str(user.id)
    context["approval_id"] = str(row.id)
    # Tenant scoping for credential resolution: use the approval row's
    # tenant, not the requester's, so cross-tenant re-runs can't happen.
    context["tenant_id"] = str(row.tenant_id)

    agent = agent_cls()
    try:
        output = await agent.run(
            AgentInput(
                task_description=row.task_description,
                context=context,
            )
        )
    except Exception as exc:
        row.execution_result = {"success": False, "error": str(exc)}
        await session.commit()
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {exc}")

    from datetime import datetime, timezone
    row.status = "approved"
    row.decided_by = user.id
    row.decided_at = datetime.now(timezone.utc)
    row.execution_result = {
        "success": output.success,
        "result": output.result,
        "error": output.error,
    }
    await session.commit()

    await audit(
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        event_type="approval.approved",
        subject_type="approval",
        subject_id=str(row.id),
        run_id=str(row.run_id) if row.run_id else None,
        payload={
            "task_id": row.task_id,
            "agent_type": row.agent_type,
            "success": output.success,
            "tasks_created": (output.result or {}).get("tasks_created", []),
            "error": output.error,
        },
    )

    return {
        "id": str(row.id),
        "status": row.status,
        "execution_result": row.execution_result,
    }
