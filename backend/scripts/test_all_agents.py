"""Batch E2E: exercise every agent through the orchestrator."""
import asyncio, sys
from pathlib import Path as _P
sys.path.insert(0, str(_P(__file__).resolve().parent.parent))
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from uuid import uuid4
from sqlalchemy import text
from app.database import SessionFactory
import app.workflows.orchestrator as orch

TENANT = "de2b2f2b-1348-4ba3-bbc8-8eaf2b09face"

TESTS = [
    ("support",   "Check support tickets about login issues"),
    ("lead",      "Find new leads from this week"),
    ("analytics", "Generate a sales report for this month"),
    ("research",  "Research Nexora AI competitors"),
    ("reporting", "Create a summary report of Q4 sales"),
    ("operations","Show me products in inventory"),
    ("email",     "Draft an email to tanasabi@gmail.com about the new pricing"),
]


async def run_one(label: str, user_request: str) -> dict:
    print(f"\n{'='*70}")
    print(f"[{label}] {user_request}")
    print('='*70)
    run_id = str(uuid4())
    try:
        result = await orch.run_orchestrator(
            user_request=user_request,
            run_id=run_id,
            tenant_id=TENANT,
        )
    except Exception as exc:
        print(f"  EXCEPTION: {type(exc).__name__}: {exc}")
        return {"label": label, "status": "exception", "error": str(exc)}

    status = result.get("status")
    print(f"  orchestrator status: {status}")
    trs = result.get("task_results", [])
    for tr in trs:
        print(f"    task {tr.get('task_id')}: status={tr.get('status')} "
              f"agent={tr.get('agent_type')} approval={tr.get('approval_id')}")
        if tr.get("error"):
            print(f"      error: {tr['error']}")
        r = tr.get("result") or {}
        for k in ("action", "to", "subject", "draft_id", "approval_id",
                  "summary", "report_id", "count", "num_results"):
            if k in r:
                print(f"      {k}: {r[k]}")

    # Audit summary
    async with SessionFactory() as s:
        async with s.begin():
            events = (await s.execute(
                text("SELECT event_type FROM audit_events WHERE run_id = :rid ORDER BY created_at"),
                {"rid": run_id},
            )).all()
    event_types = [e[0] for e in events]
    print(f"  audit events ({len(event_types)}): {event_types[:6]}")

    return {"label": label, "status": status, "task_results": trs}


async def main():
    results = []
    for label, request in TESTS:
        try:
            r = await run_one(label, request)
            results.append(r)
        except Exception as exc:
            print(f"\n[{label}] HARness failure: {type(exc).__name__}: {exc}")
            results.append({"label": label, "status": "harness_exception", "error": str(exc)})

    print("\n\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    for r in results:
        status = r.get("status")
        mark = "OK " if status in ("completed", "pending_approval") else "XX "
        print(f"  {mark} {r['label']:12s} status={status}")


asyncio.run(main())
