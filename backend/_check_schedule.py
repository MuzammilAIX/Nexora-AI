import asyncio, sys, json
from sqlalchemy import text
from app.database import SessionFactory
async def main():
    async with SessionFactory() as db:
        rows = (await db.execute(text(
            "SELECT * FROM schedule_entries WHERE tenant_id = 'e587e037-a729-4f91-9b09-08600cb62f91' "
            "ORDER BY start_at"
        ))).fetchall()
        print(f"ROWS_FOR_TENANT: {len(rows)}")
        for r in rows:
            print("  ---")
            for k, v in r._mapping.items(): print(f"    {k}: {v}")
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
