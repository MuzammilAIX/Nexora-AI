import asyncio, sys
from sqlalchemy import text
from app.database import SessionFactory
async def main():
    async with SessionFactory() as db:
        rows = (await db.execute(text(
            "SELECT id::text, title, entry_type, start_at, end_at, tenant_id::text "
            "FROM schedule_entries WHERE tenant_id = 'e587e037-a729-4f91-9b09-08600cb62f91' "
            "ORDER BY created_at DESC LIMIT 10"
        ))).fetchall()
        print(f"ENTRIES_FOR_TENANT: {len(rows)}")
        for r in rows:
            print(f"  id={r[0][:8]} title={r[1]!r} type={r[2]} start={r[3]} end={r[4]}")
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
