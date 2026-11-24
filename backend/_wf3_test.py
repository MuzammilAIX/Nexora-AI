import asyncio, sys, uuid, json
from app.workflows.orchestrator import run_orchestrator

async def main():
    req = "Generate my November business performance report and send it to nmuzammil690@gmail.com."
    b = await run_orchestrator(
        user_request=req,
        tenant_id="2857d0c5-6669-4d7d-a308-c8726bcc46bc",
        run_id=str(uuid.uuid4()),
    )
    print("TOP_LEVEL_KEYS:", list(b.keys()))
    print("TASKS:", [(t.get("agent_type"), t.get("requires_approval")) for t in b.get("tasks", [])])
    print("APPROVALS_VALUE:", json.dumps(b.get("approvals"), default=str)[:800])

    for i, r in enumerate(b.get("task_results") or []):
        res = r.get("result") or {}
        agent = r.get("agent_type")
        status = r.get("status")
        print("--- result[%d] agent=%s status=%s ---" % (i, agent, status))
        print("  keys:", list(res.keys()))
        print("  action:", res.get("action"))
        if "draft" in res:
            d = res["draft"] or {}
            print("  draft.to:", d.get("to") or d.get("recipient"))
            print("  draft.subject:", (d.get("subject") or "")[:120])
            print("  draft.body[:200]:", (d.get("body") or "")[:200])
        if "action_card" in res:
            print("  action_card:", json.dumps(res["action_card"], default=str)[:300])

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
