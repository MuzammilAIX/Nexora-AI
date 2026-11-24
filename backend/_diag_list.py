import asyncio, sys
from app.tools.schedule import list_occurrences, month_bounds
from datetime import datetime
async def main():
    now = datetime.now()
    start, end = month_bounds(now.year, now.month)
    print(f"MONTH: {now.year}-{now.month:02d}  range={start.date()} to {end.date()}")
    items = await list_occurrences("e587e037-a729-4f91-9b09-08600cb62f91", start, end)
    print(f"LIST_OCCURRENCES_COUNT: {len(items)}")
    for i in items[:3]: print(f"  {i.get(\"title\")} @ {i.get(\"start\")}")
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
