"""
Integration routes — connect / list / disconnect external services.
Credentials are encrypted via app.crypto before storage. Never returned.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..database.auth_models import User
from ..database.integration_models import (
    Integration,
    IntegrationCredential,
)
from ..auth_deps import get_current_user
from ..crypto import encrypt_token
from ..audit import audit


router = APIRouter(prefix="/integrations", tags=["Integrations"])


class ConnectHubSpotRequest(BaseModel):
    access_token: str = Field(min_length=10, description="HubSpot Service Key")


@router.get("")
async def list_integrations(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(Integration)
        .where(Integration.tenant_id == user.tenant_id)
        .order_by(Integration.connected_at.desc())
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [
        {
            "id": str(r.id),
            "provider": r.provider,
            "status": r.status,
            "connected_by": str(r.connected_by) if r.connected_by else None,
            "connected_at": r.connected_at.isoformat(),
        }
        for r in rows
    ]


@router.post("/hubspot/connect")
async def connect_hubspot(
    body: ConnectHubSpotRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    token = body.access_token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="access_token is required")

    from ..integrations.hubspot import HubSpotConnector
    import httpx
    try:
        connector = HubSpotConnector(access_token=token)
        await connector.search_contacts(query="", limit=1)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"HubSpot rejected the token ({exc.response.status_code}). Check the Service Key scopes and try again.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"HubSpot connection failed: {exc}",
        )

    existing_stmt = (
        select(Integration)
        .where(Integration.tenant_id == user.tenant_id)
        .where(Integration.provider == "hubspot")
        .limit(1)
    )
    integration = (await session.execute(existing_stmt)).scalar_one_or_none()

    if integration is None:
        integration = Integration(
            tenant_id=user.tenant_id,
            provider="hubspot",
            status="connected",
            connected_by=user.id,
        )
        session.add(integration)
        await session.flush()
    else:
        integration.status = "connected"
        integration.connected_by = user.id

    cred = IntegrationCredential(
        integration_id=integration.id,
        encrypted_token=encrypt_token(token),
    )
    session.add(cred)
    await session.commit()
    await session.refresh(integration)

    await audit(
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        event_type="integration.connected",
        subject_type="integration",
        subject_id=str(integration.id),
        payload={"provider": "hubspot"},
    )

    return {
        "id": str(integration.id),
        "provider": integration.provider,
        "status": integration.status,
    }


@router.delete("/{integration_id}")
async def disconnect_integration(
    integration_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(Integration)
        .where(Integration.id == integration_id)
        .where(Integration.tenant_id == user.tenant_id)
    )
    integration = (await session.execute(stmt)).scalar_one_or_none()
    if integration is None:
        raise HTTPException(status_code=404, detail="Integration not found")

    await session.delete(integration)
    await session.commit()

    await audit(
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        event_type="integration.disconnected",
        subject_type="integration",
        subject_id=str(integration_id),
        payload={"provider": integration.provider},
    )
    return {"id": str(integration_id), "status": "disconnected"}
