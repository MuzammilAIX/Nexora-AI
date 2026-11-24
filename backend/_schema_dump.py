import asyncio, sys
from sqlalchemy import text
from app.database import SessionFactory
async def main():
    async with SessionFactory() as db:
        for t in ("orders", "order_items"):
            cols = (await db.execute(text(
                "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
                "WHERE table_name = :t ORDER BY ordinal_position"
            ), {"t": t})).fetchall()
            print(f"\n{t}:")
            for c in cols:
                print(f"  {c[0]:30s} {c[1]:30s} null={c[2]}")
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
