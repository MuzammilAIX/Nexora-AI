import asyncio, sys, uuid
from app.workflows.orchestrator import run_orchestrator

TENANT = "e587e037-a729-4f91-9b09-08600cb62f91"

async def main():
    tests = [
        "Whats my tommor schedule",
        "provide the schedule of next days until 30 Nov 2026",
        "next 7 days schedule",
        "this week schedule",
        "what do i have this month",
        "what is my schedule for november 30",
    ]
    for q in tests:
        print("=" * 70)
        print("QUERY:", q)
        out = await run_orchestrator(user_request=q, tenant_id=TENANT, run_id=str(uuid.uuid4()))
        print("TASKS:", [(t.get("agent_type"), t.get("task_id")) for t in out.get("tasks", [])])
        for r in (out.get("task_results") or []):
            res = r.get("result") or {}
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
