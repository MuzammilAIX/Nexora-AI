import asyncio, sys
from sqlalchemy import text
from app.database import SessionFactory
async def main():
    async with SessionFactory() as db:
        rows = (await db.execute(text(
            "SELECT u.id::text, u.email, u.tenant_id::text, t.name as tenant_name "
            "FROM users u LEFT JOIN tenants t ON t.id = u.tenant_id "
            "WHERE u.email LIKE '%success%'"
        ))).fetchall()
        print("LOGGED_IN_USERS:")
        for r in rows: print(f"  email={r[1]} tenant_id={r[2]} tenant_name={r[3]}")
        print()
        entries = (await db.execute(text(
            "SELECT tenant_id::text, COUNT(*) FROM schedule_entries GROUP BY tenant_id"
        ))).fetchall()
        print("ENTRIES_BY_TENANT:")
        for e in entries: print(f"  {e[0]} -> {e[1]} entries")
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
