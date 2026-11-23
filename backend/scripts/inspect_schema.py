"""One-off schema inspection. Windows-safe (SelectorEventLoop)."""
import asyncio
import sys
from pathlib import Path

# Make `app` importable when running this file directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import text
from app.database import engine


async def main():
    async with engine.connect() as conn:
        r = await conn.execute(text(
            "SELECT tablename FROM pg_tables "
            "WHERE schemaname='public' ORDER BY tablename"
        ))
        tables = [row[0] for row in r]
        print("=== TABLES ===")
        for t in tables:
            print(" ", t)

        for tbl in ["audit_events", "users", "tenants", "runs", "approvals",
                    "agents", "agent_tools"]:
            print(f"\n=== {tbl} ===")
            r = await conn.execute(text(
                "SELECT column_name, data_type, is_nullable, column_default "
                "FROM information_schema.columns "
                "WHERE table_name = :t ORDER BY ordinal_position"
            ), {"t": tbl})
            rows = list(r)
            if not rows:
                print("  (table does not exist)")
                continue
            for row in rows:
                print(f"  {row[0]:<24} {row[1]:<28} null={row[2]:<5} default={row[3]}")

        print("\n=== agents table present? ===")
        print("  ", "agents" in tables)
        print("=== agent_tools table present? ===")
        print("  ", "agent_tools" in tables)

asyncio.run(main())
