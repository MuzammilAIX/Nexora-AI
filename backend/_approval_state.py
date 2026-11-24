import asyncio, sys, json
from sqlalchemy import text
from app.database import SessionFactory
async def main():
    async with SessionFactory() as db:
        r = (await db.execute(text(
            "SELECT id::text, status, decided_by::text, decided_at, execution_result "
            "FROM approvals WHERE id = '12cb60c0-7743-4d72-b44a-440965141839'"
        ))).fetchone()
    if not r:
        print("NOT FOUND"); return
    print("ID:", r[0])
    print("STATUS:", r[1])
    print("DECIDED_BY:", r[2])
    print("DECIDED_AT:", r[3])
    print("EXECUTION_RESULT:", json.dumps(r[4], default=str)[:800] if r[4] else None)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
