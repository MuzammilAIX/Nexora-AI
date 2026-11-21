"""Support agent E2E through orchestrator."""
import asyncio, sys
from pathlib import Path as _P
sys.path.insert(0, str(_P(__file__).resolve().parent.parent))
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from uuid import uuid4
import app.workflows.orchestrator as orch

async def m():
    run_id = str(uuid4())
    result = await orch.run_orchestrator(
        user_request="check my gmail for support emails about the system",
        run_id=run_id,
        tenant_id="de2b2f2b-1348-4ba3-bbc8-8eaf2b09face",
    )
    print(f"status: {result.get('status')}")
    for tr in result.get("task_results", []):
        print(f"\n  task {tr.get('task_id')}: status={tr.get('status')} agent={tr.get('agent_type')}")
        if tr.get("error"):
            print(f"    error: {tr['error']}")
        r = tr.get("result") or {}
        for k in ("action", "summary", "email_id", "thread_id", "approval_reason"):
            if k in r:
                print(f"    {k}: {str(r[k])[:200]}")
        if r.get("classification"):
            print(f"    classification: {r['classification']}")
        if r.get("proposed_email"):
            pe = r["proposed_email"]
            print(f"    proposed_email: to={pe.get('to')} subject={pe.get('subject')}")

asyncio.run(m())
