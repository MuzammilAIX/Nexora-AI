"""
Permission dependency. Reads Role.permissions JSONB.

Usage:
    user: User = Depends(require_permission("approve_actions"))

Falls back to legacy string role map if user.role_id is NULL
(during the transition window).
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..database.auth_models import User
from ..database.team_models import Role
from ..auth_deps import get_current_user


_LEGACY_MAP = {
    "owner": {
        "manage_members": True, "approve_actions": True,
        "manage_integrations": True, "configure_agents": True,
        "create_workflows": True, "execute_workflows": True,
        "view_analytics": True, "manage_billing": True,
    },
    "admin": {
        "manage_members": True, "approve_actions": True,
        "manage_integrations": True, "configure_agents": True,
        "create_workflows": True, "execute_workflows": True,
        "view_analytics": True, "manage_billing": False,
    },
    "manager": {
        "approve_actions": True, "create_workflows": True,
        "execute_workflows": True, "view_analytics": True,
    },
    "operator": {"execute_workflows": True, "view_analytics": True},
    "member":   {"view_analytics": True},
    "viewer":   {"view_analytics": True},
}


async def resolve_permissions(user: User, session: AsyncSession) -> dict:
    """Return the permission dict for this user, preferring role_id over legacy."""
    if user.role_id is not None:
        role = await session.get(Role, user.role_id)
        if role and role.permissions:
            return role.permissions
    return _LEGACY_MAP.get(user.role or "viewer", {})


async def user_has_permission(
    user: User, session: AsyncSession, perm: str
) -> bool:
    perms = await resolve_permissions(user, session)
    return bool(perms.get(perm, False))


def require_permission(perm: str):
    """FastAPI dependency factory."""
    async def dep(
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
    ) -> User:
        if not await user_has_permission(user, session, perm):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {perm}",
            )
        return user
    return dep
