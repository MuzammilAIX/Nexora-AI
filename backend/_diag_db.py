import asyncio, sys
from sqlalchemy import text
from app.database import SessionFactory
async def main():
    async with SessionFactory() as db:
        rows = (await db.execute(text(
            "SELECT id::text, title, start_at, tenant_id::text FROM schedule_entries "
            "ORDER BY created_at DESC LIMIT 5"
        ))).fetchall()
        print(f"TOTAL_ENTRIES: {len(rows)}")
        for r in rows: print(f"  tenant={r[3][:8]} title={r[1]!r} start={r[2]}")
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
