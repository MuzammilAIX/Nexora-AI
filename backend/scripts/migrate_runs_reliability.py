"""Add reliability columns to the `runs` table (the actual workflow-execution table)."""
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
ALTER TABLE runs ADD COLUMN IF NOT EXISTS retry_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS last_error TEXT;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMP WITH TIME ZONE;
CREATE INDEX IF NOT EXISTS idx_runs_status_retry ON runs(status, next_retry_at);
CREATE INDEX IF NOT EXISTS idx_runs_status_created ON runs(status, created_at);
"""

async def main() -> None:
    async with SessionFactory() as session:
        async with session.begin():
            for stmt in DDL.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    await session.execute(text(stmt))
    print("Migration complete:")
    print("  + runs: retry_count, last_error, next_retry_at")
    print("  + index: idx_runs_status_retry")
    print("  + index: idx_runs_status_created")
    print("  (state_json already serves as checkpoint_data)")

if __name__ == "__main__":
    asyncio.run(main())
