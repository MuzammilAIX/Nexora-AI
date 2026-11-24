import asyncio, sys, uuid
from app.workflows.orchestrator import run_orchestrator

TENANT = "e587e037-a729-4f91-9b09-08600cb62f91"

async def main():
    print("=" * 70)
    print("TEST 1: Multi-month report -> requires approval")
    out = await run_orchestrator(
        user_request="Generate sales report from Jan 2026 to Nov 2026",
        tenant_id=TENANT, run_id=str(uuid.uuid4()),
    )
    for r in (out.get("task_results") or []):
        if r.get("agent_type") == "analytics":
            res = r.get("result") or {}
            print("  status:", r.get("status"))
            print("  requires_approval:", res.get("requires_approval"))
            print("  action_kind:", res.get("action_kind"))
            print("  approval_reason:", res.get("approval_reason"))
            print("  approval_id:", r.get("approval_id") or res.get("approval_id"))

    print()
    print("TEST 2: Single-month report -> NO approval")
    out2 = await run_orchestrator(
        user_request="Generate sales report for October 2026",
        tenant_id=TENANT, run_id=str(uuid.uuid4()),
    )
    for r in (out2.get("task_results") or []):
        if r.get("agent_type") == "analytics":
            res = r.get("result") or {}
            print("  status:", r.get("status"))
            print("  requires_approval:", res.get("requires_approval"))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
