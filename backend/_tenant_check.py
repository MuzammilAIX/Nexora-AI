import asyncio, sys
from sqlalchemy import text
from app.database import SessionFactory

async def main():
    async with SessionFactory() as db:
        print("=== ALL APPROVALS (with tenant) ===")
        rows = (await db.execute(text(
            "SELECT id::text, agent_type, status, tenant_id::text, run_id::text, created_at "
            "FROM approvals ORDER BY created_at DESC LIMIT 10"
        ))).fetchall()
        for r in rows:
            print(" ", r)

        print("\n=== USERS (find the logged-in one) ===")
        users = (await db.execute(text(
            "SELECT id::text, email, tenant_id::text FROM users WHERE email ILIKE '%success%' LIMIT 5"
        ))).fetchall()
        for u in users:
            print(" ", u)

        print("\n=== TENANTS (name + id) ===")
        tenants = (await db.execute(text("SELECT id::text, name FROM tenants LIMIT 10"))).fetchall()
        for t in tenants:
            print(" ", t)

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
