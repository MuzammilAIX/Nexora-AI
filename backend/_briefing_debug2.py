import asyncio, sys, traceback
from app.agents.briefing import BriefingAgent, _parse_range
from app.agents.base import AgentInput
from datetime import date

TENANT = "e587e037-a729-4f91-9b09-08600cb62f91"

async def main():
    agent = BriefingAgent()
    tests = [
        "provide the schedule of next days until 30 Nov 2026",
        "next 7 days schedule",
        "this week schedule",
        "what do i have this month",
    ]
    for q in tests:
        print("=" * 60)
        print("QUERY:", q)
        try:
            parsed = _parse_range(q, date(2026, 11, 24))
            print("  _parse_range returned:", parsed)
        except Exception as e:
            print("  _parse_range ERROR:", type(e).__name__, str(e))
            traceback.print_exc()
        try:
            out = await agent.run(AgentInput(
                task_description=q,
                context={"tenant_id": TENANT, "user_request": q},
            ))
            res = out.result or {}
            print("  agent result: action=", res.get("action"), "items=", len(res.get("items") or []))
            print("  formatted:", (res.get("formatted") or "")[:200])
        except Exception as e:
            print("  agent ERROR:", type(e).__name__, str(e))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
