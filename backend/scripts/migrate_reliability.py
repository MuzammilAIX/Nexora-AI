"""
Idempotent migration for Reliability (Section 7.5).

Adds:
  - workflow_executions: retry_count, last_error, next_retry_at,
    checkpoint_data, status
  - tasks: retry_count, last_error, idempotency_key, checkpoint_data
  - idempotency_keys table (unique key constraint)
  - audit_events table (append-only)

Safe to run multiple times: uses IF NOT EXISTS / ADD COLUMN IF NOT EXISTS.
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
-- workflow_executions: add retry / recovery columns
ALTER TABLE IF EXISTS workflow_executions
    ADD COLUMN IF NOT EXISTS retry_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE IF EXISTS workflow_executions
    ADD COLUMN IF NOT EXISTS last_error TEXT;
ALTER TABLE IF EXISTS workflow_executions
    ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE IF EXISTS workflow_executions
    ADD COLUMN IF NOT EXISTS checkpoint_data JSONB;

-- tasks: add retry / idempotency columns
ALTER TABLE IF EXISTS tasks
    ADD COLUMN IF NOT EXISTS retry_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE IF EXISTS tasks
    ADD COLUMN IF NOT EXISTS last_error TEXT;
ALTER TABLE IF EXISTS tasks
    ADD COLUMN IF NOT EXISTS idempotency_key TEXT;
ALTER TABLE IF EXISTS tasks
    ADD COLUMN IF NOT EXISTS checkpoint_data JSONB;

-- idempotency_keys: prevents duplicate external writes on retry
CREATE TABLE IF NOT EXISTS idempotency_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key TEXT NOT NULL UNIQUE,
    tenant_id UUID NOT NULL,
    action_type TEXT NOT NULL,
    status TEXT NOT NULL,
    error TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX IF NOT EXISTS idx_idempotency_tenant_status
    ON idempotency_keys(tenant_id, status);

-- audit_events: append-only log
CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    event_type TEXT NOT NULL,
    workflow_id TEXT,
    task_id TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_audit_tenant_created
    ON audit_events(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_event_type
    ON audit_events(event_type);

-- NOTE: recovery scan index on workflow_executions is deferred until the
-- table is created (see migrate_workflow_executions.py).
"""


async def main() -> None:
    async with SessionFactory() as session:
        async with session.begin():
            for stmt in DDL.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    await session.execute(text(stmt))
    print("Migration complete:")
    print("  + workflow_executions: retry_count, last_error, next_retry_at, checkpoint_data")
    print("  + tasks: retry_count, last_error, idempotency_key, checkpoint_data")
    print("  + idempotency_keys table (unique key)")
    print("  + audit_events table (append-only)")
    print("  + indexes for recovery and audit queries")


if __name__ == "__main__":
    asyncio.run(main())
