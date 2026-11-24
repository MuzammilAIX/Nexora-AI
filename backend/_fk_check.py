import asyncio, sys
from sqlalchemy import text
from app.database import SessionFactory
async def main():
    async with SessionFactory() as db:
        # What FKs does orders have?
        fks = (await db.execute(text(
            "SELECT a.attname, c.confrelid::regclass::text "
            "FROM pg_constraint c "
            "JOIN pg_attribute a ON a.attnum = ANY(c.conkey) AND a.attrelid = c.conrelid "
            "WHERE c.conrelid = 'orders'::regclass AND c.contype = 'f'"
        ))).fetchall()
        print("ORDERS_FKS:", fks)
        # Does customers table exist?
        exists = (await db.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'customers')"
        ))).scalar()
        print("CUSTOMERS_TABLE_EXISTS:", exists)
        if exists:
            cnt = (await db.execute(text("SELECT COUNT(*) FROM customers"))).scalar()
            print("CUSTOMERS_COUNT:", cnt)
            sample = (await db.execute(text(
                "SELECT id::text, tenant_id::text FROM customers LIMIT 5"
            ))).fetchall()
            print("CUSTOMERS_SAMPLE:", sample)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
