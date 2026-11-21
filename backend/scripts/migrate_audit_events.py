"""Add missing workflow_id and task_id columns to audit_events if they don't exist."""
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
ALTER TABLE audit_events
    ADD COLUMN IF NOT EXISTS workflow_id TEXT;
ALTER TABLE audit_events
    ADD COLUMN IF NOT EXISTS task_id TEXT;
ALTER TABLE audit_events
    ADD COLUMN IF NOT EXISTS payload JSONB;
"""


async def main() -> None:
    async with SessionFactory() as session:
        async with session.begin():
            for stmt in DDL.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    await session.execute(text(stmt))
    print("audit_events migration complete:")
    print("  + workflow_id (TEXT) — added if missing")
    print("  + task_id (TEXT)     — added if missing")
    print("  + payload (JSONB)    — added if missing")


if __name__ == "__main__":
    asyncio.run(main())
