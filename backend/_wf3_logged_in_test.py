import asyncio, sys, uuid, json
from app.workflows.orchestrator import run_orchestrator

async def main():
    b = await run_orchestrator(
        user_request="Generate my November business performance report and send it to nmuzammil690@gmail.com.",
        tenant_id="e587e037-a729-4f91-9b09-08600cb62f91",   # ← the LOGGED-IN user's tenant
        run_id=str(uuid.uuid4()),
    )
    print("RUN_ID:", b.get("run_id"))
    print("TASKS:", [(t.get("agent_type"), t.get("requires_approval")) for t in b.get("tasks", [])])
    for i, r in enumerate(b.get("task_results") or []):
        res = r.get("result") or {}
        print("result[%d] agent=%s status=%s" % (i, r.get("agent_type"), r.get("status")))
        print("  keys:", list(res.keys()))
        if res.get("action"):
            print("  action:", res.get("action"))
    # Confirm approval row landed under the right tenant:
    from sqlalchemy import text
    from app.database import SessionFactory
    async with SessionFactory() as db:
        rows = (await db.execute(text(
            "SELECT id::text, agent_type, status, tenant_id::text, run_id::text "
            "FROM approvals WHERE tenant_id = 'e587e037-a729-4f91-9b09-08600cb62f91' "
            "ORDER BY created_at DESC LIMIT 3"
        ))).fetchall()
        print("\nAPPROVALS_FOR_LOGGED_IN_TENANT:")
        for r in rows: print("  ", r)

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
