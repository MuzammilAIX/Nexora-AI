import asyncio, sys, traceback
from datetime import date
from app.agents.briefing import _parse_range, _format_range
from app.tools.schedule import list_occurrences

TENANT = "e587e037-a729-4f91-9b09-08600cb62f91"

async def main():
    tests = [
        "provide the schedule of next days until 30 Nov 2026",
        "next 7 days schedule",
    ]
    for q in tests:
        print("=" * 60)
        print("QUERY:", q)
        start, end = _parse_range(q, date(2026, 11, 24))
        print("  range:", start, "->", end)
        try:
            items = await list_occurrences(TENANT, start, end)
            print("  list_occurrences count:", len(items))
            if items:
                print("  first item type:", type(items[0]).__name__)
                print("  first item:", str(items[0])[:300])
        except Exception as e:
            print("  LIST_OCCURRENCES ERROR:", type(e).__name__, str(e))
            traceback.print_exc()
            continue
        try:
            formatted = _format_range(items, start, end)
            print("  formatted (first 5 lines):")
            for line in formatted.split(chr(10))[:5]:
                print("    " + line)
        except Exception as e:
            print("  FORMAT_RANGE ERROR:", type(e).__name__, str(e))
            traceback.print_exc()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
