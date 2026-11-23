"""
Team & Permissions API.

All endpoints enforce tenant isolation (user.tenant_id) and appropriate
permissions. Every mutating action writes to audit_events.
"""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..database.auth_models import User
from ..database.team_models import Role, Invitation
from ..auth_deps import get_current_user
from ..deps.permissions import require_permission
from ..tools.audit import log_event


router = APIRouter(prefix="/team", tags=["Team"])


# ---------------- Schemas ----------------

class InviteRequest(BaseModel):
    email: EmailStr
    role_id: UUID


class ChangeRoleRequest(BaseModel):
    role_id: UUID


# ---------------- Helpers ----------------

async def _audit(
    user: User, action: str, target: str, payload: dict | None = None
) -> None:
    await log_event(
        tenant_id=str(user.tenant_id),
        event_type=f"team.{action}",
        subject_type="user",
        subject_id=target,
        payload=payload or {},
        actor_user_id=user.id,
        actor_type="user",
        actor_label=user.email,
        severity="info",
    )


async def _get_role_or_404(
    session: AsyncSession, role_id: UUID, tenant_id: UUID
) -> Role:
    """Role is accessible if it is a system role OR belongs to this tenant."""
    role = await session.get(Role, role_id)
    if role is None:
        raise HTTPException(404, "Role not found")
    if not role.is_system and role.tenant_id != tenant_id:
        raise HTTPException(404, "Role not found")
    return role


# ---------------- Endpoints ----------------

@router.get("/members")
async def list_members(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    rows = (await session.execute(
        select(User, Role)
        .outerjoin(Role, User.role_id == Role.id)
        .where(User.tenant_id == user.tenant_id)
        .where(User.deleted_at.is_(None))
        .order_by(User.created_at)
    )).all()

    return [
        {
            "id": str(u.id),
            "email": u.email,
            "role": u.role,
            "role_id": str(u.role_id) if u.role_id else None,
            "role_name": r.name if r else None,
            "status": u.status,
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
            "created_at": u.created_at.isoformat(),
        }
        for u, r in rows
    ]


@router.get("/roles")
async def list_roles(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    rows = (await session.execute(
        select(Role).where(
            (Role.is_system.is_(True)) | (Role.tenant_id == user.tenant_id)
        ).order_by(Role.is_system.desc(), Role.name)
    )).scalars().all()

    return [
        {
            "id": str(r.id),
            "name": r.name,
            "description": r.description,
            "is_system": r.is_system,
            "permissions": r.permissions,
        }
        for r in rows
    ]


@router.post("/invite")
async def invite_member(
    body: InviteRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("manage_members")),
):
    existing = (await session.execute(
        select(Invitation).where(
            Invitation.tenant_id == user.tenant_id,
            Invitation.email == body.email,
            Invitation.status == "pending",
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "Pending invitation already exists for this email")

    already = (await session.execute(
        select(User).where(
            User.tenant_id == user.tenant_id,
            User.email == body.email,
            User.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if already:
        raise HTTPException(409, "User already exists in this organization")

    await _get_role_or_404(session, body.role_id, user.tenant_id)

    raw_token = token_urlsafe(32)
    token_hash = sha256(raw_token.encode()).hexdigest()

    inv = Invitation(
        tenant_id=user.tenant_id,
        email=body.email,
        role_id=body.role_id,
        token_hash=token_hash,
        invited_by=user.id,
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    session.add(inv)
    await session.commit()
    await session.refresh(inv)

    await _audit(user, "invited", body.email, {"role_id": str(body.role_id)})

    # TODO: integrate email sending. debug_token only for local testing.
    return {
        "invitation_id": str(inv.id),
        "email": inv.email,
        "expires_at": inv.expires_at.isoformat(),
        "debug_token": raw_token,
    }


@router.get("/invitations")
async def list_invitations(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("manage_members")),
):
    rows = (await session.execute(
        select(Invitation)
        .where(Invitation.tenant_id == user.tenant_id)
        .order_by(Invitation.created_at.desc())
    )).scalars().all()
    return [
        {
            "id": str(i.id),
            "email": i.email,
            "role_id": str(i.role_id),
            "status": i.status,
            "expires_at": i.expires_at.isoformat(),
            "created_at": i.created_at.isoformat(),
        }
        for i in rows
    ]


@router.patch("/members/{user_id}/role")
async def change_role(
    user_id: UUID,
    body: ChangeRoleRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("manage_members")),
):
    target = await session.get(User, user_id)
    if target is None or target.tenant_id != user.tenant_id or target.deleted_at is not None:
        raise HTTPException(404, "User not found")

    role = await _get_role_or_404(session, body.role_id, user.tenant_id)

    old_role = target.role
    target.role = role.name
    target.role_id = role.id
    await session.commit()

    await _audit(
        user, "role_changed", str(target.id),
        {"old_role": old_role, "new_role": role.name},
    )
    return {"ok": True, "new_role": role.name}


@router.post("/members/{user_id}/suspend")
async def suspend_member(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("manage_members")),
):
    if user_id == user.id:
        raise HTTPException(400, "Cannot suspend yourself")

    target = await session.get(User, user_id)
    if target is None or target.tenant_id != user.tenant_id:
        raise HTTPException(404, "User not found")

    target.status = "suspended"
    await session.commit()
    await _audit(user, "suspended", str(target.id))
    return {"ok": True}


@router.delete("/members/{user_id}")
async def remove_member(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("manage_members")),
):
    if user_id == user.id:
        raise HTTPException(400, "Cannot remove yourself")

    target = await session.get(User, user_id)
    if target is None or target.tenant_id != user.tenant_id:
        raise HTTPException(404, "User not found")

    target.deleted_at = datetime.now(timezone.utc)
    target.status = "removed"
    await session.commit()
    await _audit(user, "removed", str(target.id))
    return {"ok": True}
