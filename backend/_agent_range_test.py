import asyncio, sys
from app.agents.briefing import BriefingAgent
from app.agents.base import AgentInput

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
        out = await agent.run(AgentInput(
            task_description=q,
            context={"tenant_id": TENANT, "user_request": q},
        ))
        print("  success:", out.success)
        if not out.success:
            print("  error:", out.error)
            continue
        res = out.result or {}
        print("  action:", res.get("action"))
        print("  range:", res.get("range_start"), "to", res.get("range_end"))
        print("  items:", len(res.get("items") or []))
        print("  formatted (first 8 lines):")
        for line in (res.get("formatted") or "").split(chr(10))[:8]:
            print("    " + line)
        print()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
