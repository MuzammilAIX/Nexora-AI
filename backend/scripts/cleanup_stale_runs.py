"""One-time cleanup: mark stale pending_approval runs as failed, and
clear recoverable failed runs that have no completion path."""
import asyncio, sys
from pathlib import Path as _P
sys.path.insert(0, str(_P(__file__).resolve().parent.parent))
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from app.database import SessionFactory

async def main():
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)

    async with SessionFactory() as session:
        async with session.begin():
            # 1. Stale approvals older than 30 min -> mark failed
            r1 = await session.execute(
                text(
                    "UPDATE runs SET status='failed', "
                    "last_error='stale_approval_cleanup', "
                    "completed_at=NOW() "
                    "WHERE status='pending_approval' AND created_at < :cutoff"
                ),
                {"cutoff": cutoff},
            )
            # 2. Old failed runs with state_json -> clear state (they're unrecoverable now)
            r2 = await session.execute(
                text(
                    "UPDATE runs SET state_json=NULL "
                    "WHERE status='failed' AND state_json IS NOT NULL "
                    "AND created_at < :cutoff"
                ),
                {"cutoff": cutoff},
            )
    print(f"cleaned: {r1.rowcount} stale approvals, {r2.rowcount} stale state_json blobs")

asyncio.run(main())
