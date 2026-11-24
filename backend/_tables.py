import asyncio, sys
from sqlalchemy import text
from app.database import SessionFactory
async def main():
    async with SessionFactory() as db:
        tables = (await db.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND (table_name ILIKE '%calendar%' OR table_name ILIKE '%event%' OR table_name ILIKE '%schedule%')"
        ))).fetchall()
        print("TABLES:", [t[0] for t in tables])
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
