import asyncio
import sys

# Windows fix — psycopg async needs SelectorEventLoop, not ProactorEventLoop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.database import engine

async def check():
    async with engine.connect() as c:
        for table in ["approvals", "integrations", "integration_credentials", "agents"]:
            r = await c.exec_driver_sql(f"SELECT to_regclass(\u0027public.{table}\u0027)")
            print(f"{table:30} = {r.fetchone()[0]}")
        print()
        r = await c.exec_driver_sql("SELECT column_name FROM information_schema.columns WHERE table_name=\u0027approvals\u0027 AND column_name=\u0027decided_reason\u0027")
        v = r.fetchone()
        print(f"decided_reason exists in approvals: {v is not None}")
        r = await c.exec_driver_sql("SELECT version_num FROM alembic_version")
        v = r.fetchone()
        print(f"alembic_version row: {v}")

asyncio.run(check())
