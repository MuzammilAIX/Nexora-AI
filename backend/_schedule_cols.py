import asyncio, sys
from sqlalchemy import text
from app.database import SessionFactory
async def main():
    async with SessionFactory() as db:
        cols = (await db.execute(text(
            "SELECT column_name, data_type, is_nullable, column_default "
            "FROM information_schema.columns WHERE table_name = 'schedule_entries' "
            "ORDER BY ordinal_position"
        ))).fetchall()
        for c in cols: print(f"  {c[0]:25s} {c[1]:30s} null={c[2]:3s} default={c[3]}")
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
