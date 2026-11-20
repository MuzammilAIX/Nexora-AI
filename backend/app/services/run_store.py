import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import Run


async def create_run(
    session: AsyncSession,
    user_request: str,
    tenant_id: UUID,
    user_id: UUID,
) -> Run:
    run = Run(
        user_request=user_request,
        status="running",
        tenant_id=tenant_id,
        user_id=user_id,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


async def complete_run(
    session: AsyncSession, run_id: UUID, state: dict, status: str
) -> Run | None:
    result = await session.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if run is None:
        return None
    run.state_json = json.dumps(state, default=str)
    run.status = status
    run.completed_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(run)
    return run


async def get_run(
    session: AsyncSession,
    run_id: UUID,
    tenant_id: UUID,
) -> Run | None:
    result = await session.execute(
        select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def list_runs(
    session: AsyncSession,
    tenant_id: UUID,
    limit: int = 20,
) -> list[Run]:
    result = await session.execute(
        select(Run)
        .where(Run.tenant_id == tenant_id)
        .order_by(desc(Run.created_at))
        .limit(limit)
    )
    return list(result.scalars().all())
