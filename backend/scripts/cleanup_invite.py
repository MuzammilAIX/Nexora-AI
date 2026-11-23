"""Clean up orphan invitation from failed invite attempt."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import text
from app.database import engine


async def main():
    async with engine.connect() as conn:
        async with conn.begin():
            r = await conn.execute(
                text("DELETE FROM invitations WHERE email = :e"),
                {"e": "newperson@example.com"},
            )
            print(f"deleted invitations: {r.rowcount}")
        async with conn.begin():
            r = await conn.execute(
                text("DELETE FROM audit_events WHERE subject_id = :e"),
                {"e": "newperson@example.com"},
            )
            print(f"deleted audit rows: {r.rowcount}")


asyncio.run(main())
