"""
Audit log routes — read-only, tenant-scoped.

No POST, PATCH, or DELETE. Append-only by design.
"""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..database.audit_models import AuditEvent
from ..database.auth_models import User
from ..auth_deps import get_current_user


router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("")
async def list_audit_events(
    limit: int = 100,
    event_type: str | None = None,
    subject_id: str | None = None,
    run_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    limit = max(1, min(limit, 500))

    stmt = select(AuditEvent).where(AuditEvent.tenant_id == user.tenant_id)

    if event_type:
        stmt = stmt.where(AuditEvent.event_type == event_type)
    if subject_id:
        stmt = stmt.where(AuditEvent.subject_id == subject_id)
    if run_id:
        stmt = stmt.where(AuditEvent.run_id == run_id)

    stmt = stmt.order_by(AuditEvent.created_at.desc()).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()

    return [
        {
            "id": str(r.id),
            "event_type": r.event_type,
            "subject_type": r.subject_type,
            "subject_id": r.subject_id,
            "run_id": str(r.run_id) if r.run_id else None,
            "actor_user_id": str(r.actor_user_id) if r.actor_user_id else None,
            "payload": r.payload,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
