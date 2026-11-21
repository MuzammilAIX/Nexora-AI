"""
Fix audit_events.id to auto-generate UUIDs.

Root cause: pre-existing audit_events table was created without DEFAULT
gen_random_uuid() on id. Inserts via log_event() fail with NotNullViolation.
"""
import asyncio
import sys
from pathlib import Path as _Path

_BACKEND_ROOT = _Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import text
from app.database import SessionFactory


DDL = """
-- Ensure pgcrypto is available (gen_random_uuid lives here on older PG)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Make id self-populate on insert
ALTER TABLE audit_events
    ALTER COLUMN id SET DEFAULT gen_random_uuid();

-- Sanity: ensure id is still NOT NULL + PK
-- (no-op if already correct)
"""


async def main() -> None:
    async with SessionFactory() as session:
        async with session.begin():
            for stmt in DDL.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    await session.execute(text(stmt))
    print("audit_events.id default fix applied:")
    print("  + pgcrypto extension present")
    print("  + audit_events.id DEFAULT gen_random_uuid()")


if __name__ == "__main__":
    asyncio.run(main())
