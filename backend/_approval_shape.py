import asyncio, sys, json
from sqlalchemy import text
from app.database import SessionFactory
async def main():
    async with SessionFactory() as db:
        # First: what columns DOES approvals have?
        cols = (await db.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'approvals' ORDER BY ordinal_position"
        ))).fetchall()
        print("APPROVALS_COLUMNS:", [c[0] for c in cols])
        print()
        # Now query the failing approval
        r = (await db.execute(text(
            "SELECT id::text, agent_type, proposed_action, reason, status "
            "FROM approvals WHERE id = '12cb60c0-7743-4d72-b44a-440965141839'"
        ))).fetchone()
    if not r:
        print("NOT FOUND"); return
    print("AGENT:", r[1])
    print("STATUS:", r[4])
    print("REASON:", r[3])
    pa = r[2]
    print("PROPOSED_ACTION_KEYS:", list((pa or {}).keys()) if pa else None)
    print("PROPOSED_ACTION:", json.dumps(pa, default=str, indent=2)[:2500] if pa else None)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
