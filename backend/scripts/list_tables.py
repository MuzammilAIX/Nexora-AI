"""List all tables in public schema."""
import asyncio
import sys
from pathlib import Path

# Go up from backend/scripts/ to backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import text
from app.database import engine


async def main():
    async with engine.connect() as conn:
        r = await conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' ORDER BY table_name"
            )
        )
        for row in r:
            print(row[0])


asyncio.run(main())
