import asyncio, sys, json, uuid
from app.workflows.orchestrator import run_orchestrator

TENANT = "e587e037-a729-4f91-9b09-08600cb62f91"

async def main():
    out = await run_orchestrator(
        user_request="what is my tomorrow schedule",
        tenant_id=TENANT,
        run_id=str(uuid.uuid4()),
    )
    print("TASKS:", [(t.get("agent_type"), t.get("task_id")) for t in out.get("tasks", [])])
    print()
    for r in (out.get("task_results") or []):
        print("=== agent:", r.get("agent_type"), "status:", r.get("status"), "===")
        res = r.get("result") or {}
        print("  keys:", list(res.keys()))
        print("  items_count:", len(res.get("items") or []))
        print("  formatted:", (res.get("formatted") or "")[:300])

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
