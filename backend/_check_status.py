import asyncio, sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select
from app.database.approval_models import Approval
from app.config import settings

async def main():
    eng = create_async_engine(settings.DATABASE_URL, echo=False)
    async with AsyncSession(eng) as s:
        stmt = select(Approval).order_by(Approval.created_at.desc()).limit(5)
        for r in (await s.execute(stmt)).scalars().all():
            pa = r.proposed_action or {}
            ex = r.execution_result or {}
            print(f"{r.id} | agent={r.agent_type} | status={r.status!r} | kind={pa.get('action_kind')!r} | exec_success={ex.get('success')}")
    await eng.dispose()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
