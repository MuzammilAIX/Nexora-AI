"""Lead agent E2E through the orchestrator."""
import asyncio, sys
from pathlib import Path as _P
sys.path.insert(0, str(_P(__file__).resolve().parent.parent))
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from uuid import uuid4
import app.workflows.orchestrator as orch

TENANT = "de2b2f2b-1348-4ba3-bbc8-8eaf2b09face"

async def m():
    run_id = str(uuid4())
    result = await orch.run_orchestrator(
        user_request="find new leads from this week and score them",
        run_id=run_id,
        tenant_id=TENANT,
    )
    print(f"status: {result.get('status')}")
    for tr in result.get("task_results", []):
        print(f"\n  task {tr.get('task_id')}: status={tr.get('status')} "
              f"agent={tr.get('agent_type')} approval={tr.get('approval_id')}")
        if tr.get("error"):
            print(f"    error: {tr['error']}")
        r = tr.get("result") or {}
        if r.get("summary"):
            print(f"    summary: {str(r['summary'])[:300]}")
        if r.get("scored_leads"):
            leads = r["scored_leads"]
            print(f"    scored_leads: {len(leads)}")
            for l in leads[:5]:
                print(f"      score={l.get('score'):3d}  name={l.get('name','?'):30s}  "
                      f"email={l.get('email','')}")
                if l.get("score_rationale"):
                    print(f"        rationale: {l['score_rationale'][:120]}")
        if r.get("tasks_created"):
            print(f"    tasks_created: {r['tasks_created']}")
        if r.get("gaps"):
            print(f"    gaps: {r['gaps']}")

asyncio.run(m())
