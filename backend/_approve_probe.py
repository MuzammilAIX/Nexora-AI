import asyncio, sys, traceback, json
from app.routes.approvals import _APPROVABLE_AGENTS, _APPROVABLE_ACTIONS
from app.database import SessionFactory
from sqlalchemy import text

async def main():
    async with SessionFactory() as db:
        row = (await db.execute(text(
            "SELECT id::text, agent_type, status, payload, proposed_action, run_id::text "
            "FROM approvals WHERE id = '12cb60c0-7743-4d72-b44a-440965141839'"
        ))).fetchone()
    if not row:
        print("APPROVAL NOT FOUND")
        return
    print("AGENT_TYPE:", row[1])
    print("STATUS:", row[2])
    print("PROPOSED_ACTION:", json.dumps(row[4], default=str)[:500] if row[4] else None)
    print("PAYLOAD_KEYS:", list((row[3] or {}).keys()) if row[3] else None)
    agent_cls = _APPROVABLE_AGENTS.get(row[1])
    print("AGENT_CLASS:", agent_cls.__name__ if agent_cls else None)
    # Try to actually run the execution path
    from app.routes.approvals import _execute_approval
    try:
        async with SessionFactory() as db:
            res = await _execute_approval(db, row[0])
            print("EXECUTE_RESULT:", json.dumps(res, default=str)[:800] if res else res)
    except Exception as e:
        print("EXECUTE_EXCEPTION:", type(e).__name__, str(e))
        traceback.print_exc()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
