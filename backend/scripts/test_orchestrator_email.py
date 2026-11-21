"""E2E: natural-language send-email through the orchestrator."""
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

async def main():
    user_request = (
        "Send an email to tanasabi@gmail.com with subject 'Nexora system is live' "
        "and body 'The Nexora AI platform is now fully operational. "
        "This email was sent by the orchestrator through the operations agent.'"
    )
    print(f"user_request:\n  {user_request}\n")

    run_id = str(uuid4())
    result = await orch.run_orchestrator(
        user_request=user_request,
        run_id=run_id,
        tenant_id=TENANT,
    )
    print(f"orchestrator status: {result.get('status')}")

    trs = result.get("task_results", [])
    for tr in trs:
        print(f"  task {tr.get('task_id')}: status={tr.get('status')} "
              f"agent={tr.get('agent_type')} approval={tr.get('approval_id')}")
        r = tr.get("result") or {}
        for k in ("action", "to", "subject", "draft_id", "approval_id", "reason"):
            if k in r:
                print(f"    {k}: {r[k]}")

    # If an approval was created, approve and execute it via the same code
    # path the API uses. The approval row holds the proposed action.
    approval_id = None
    for tr in trs:
        if tr.get("status") == "pending_approval":
            approval_id = tr.get("approval_id")
            break

    if approval_id:
        print(f"\napproval pending: {approval_id}")
        print("Approve in the UI or via POST /api/v1/approvals/{id}/approve,")
        print("then re-run this script with the approval_id to verify execution.")

    # Print audit trail for the run
    async with SessionFactory() as s:
        async with s.begin():
            rows = (await s.execute(
                text(
                    "SELECT event_type, subject_id, payload "
                    "FROM audit_events WHERE run_id = :rid ORDER BY created_at"
                ),
                {"rid": run_id},
            )).mappings().all()
    print(f"\naudit events for this run ({len(rows)}):")
    for r in rows:
        print(f"  {r['event_type']}  subj={r['subject_id']}")


asyncio.run(main())
