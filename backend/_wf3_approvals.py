import asyncio, sys
from sqlalchemy import text
from app.database import SessionFactory

async def main():
    async with SessionFactory() as db:
        rows = (await db.execute(text(
            "SELECT id::text, agent_type, status, run_id::text, created_at FROM approvals ORDER BY created_at DESC LIMIT 5"
        ))).fetchall()
        print("LATEST_APPROVALS:")
        for r in rows:
            print("  ", r)

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
