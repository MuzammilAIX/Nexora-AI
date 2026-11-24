import asyncio, sys, json
from datetime import datetime, timedelta, timezone
from app.tools.schedule import list_occurrences, month_bounds, ensure_aware
from app.database import SessionFactory
from sqlalchemy import text

TENANT = "e587e037-a729-4f91-9b09-08600cb62f91"

async def main():
    now = datetime.now()
    start, end = month_bounds(now.year, now.month)
    print(f"MONTH_RANGE: {start.date()} -> {end.date()}")
    items = await list_occurrences(TENANT, start, end)
    print(f"MONTH_ENTRIES: {len(items)}")
    for i in items[:5]: print("  ", i.get("title"), i.get("start"))

    # Simulate a create
    async with SessionFactory() as db:
        from uuid import uuid4
        test_id = str(uuid4())
        test_start = datetime.now(timezone.utc).replace(hour=14, minute=0, second=0, microsecond=0)
        test_end = test_start + timedelta(hours=1)
        await db.execute(text(
            "INSERT INTO schedule_entries (id, tenant_id, title, entry_type, start_at, end_at, all_day, created_at) "
            "VALUES (:id, :t, :title, 'meeting', :start, :end, false, NOW())"
        ), {"id": test_id, "t": TENANT, "title": "TEST EVENT FROM API PROBE", "start": test_start, "end": test_end})
        await db.commit()
        print(f"INSERTED_TEST_EVENT: {test_id}")

    # Read back
    items2 = await list_occurrences(TENANT, start, end)
    print(f"AFTER_INSERT: {len(items2)} entries")
    for i in items2[:5]: print("  ", i.get("title"), i.get("start"))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
