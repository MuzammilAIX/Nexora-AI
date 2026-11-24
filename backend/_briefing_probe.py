import asyncio, sys, json
from app.agents.briefing import build_briefing
from datetime import datetime, timezone
async def main():
    data = await build_briefing("e587e037-a729-4f91-9b09-08600cb62f91", datetime.now(timezone.utc).date())
    print("KEYS:", list(data.keys()))
    print("ITEMS_COUNT:", len(data.get("items") or []))
    print("ITEMS:", json.dumps(data.get("items"), default=str, indent=2)[:2000])
    print("PENDING_APPROVALS_COUNT:", len(data.get("pending_approvals") or []))
    print("FORMATTED:", (data.get("formatted") or "")[:500])
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
