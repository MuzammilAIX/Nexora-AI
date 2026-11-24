import asyncio, sys
from datetime import datetime, timedelta, date
from app.tools.briefing import build_briefing
from app.database import SessionFactory
from sqlalchemy import text

TENANT = "e587e037-a729-4f91-9b09-08600cb62f91"

async def main():
    today = date.today()
    tomorrow = today + timedelta(days=1)
    print("TODAY:", today)
    print("TOMORROW:", tomorrow)

    print()
    print("--- TODAY briefing ---")
    data_today = await build_briefing(TENANT, today)
    items_today = data_today.get("items") or []
    print("  items_count:", len(items_today))
    for i in items_today:
        print("   ", i.get("title"), "@", i.get("start"))

    print()
    print("--- TOMORROW briefing ---")
    data_tmrw = await build_briefing(TENANT, tomorrow)
    items_tmrw = data_tmrw.get("items") or []
    print("  items_count:", len(items_tmrw))
    for i in items_tmrw:
        print("   ", i.get("title"), "@", i.get("start"))

    print()
    print("--- ALL schedule_entries ---")
    async with SessionFactory() as db:
        rows = (await db.execute(text(
            "SELECT title, start_at::text FROM schedule_entries WHERE tenant_id = :t ORDER BY start_at"
        ), {"t": TENANT})).fetchall()
        for r in rows:
            print("  ", r[0], "@", r[1])

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
