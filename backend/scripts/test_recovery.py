"""Test 3 (runs variant): recovery scan finds failed runs with state_json and logs audit."""
import asyncio, sys
from pathlib import Path as _P
sys.path.insert(0, str(_P(__file__).resolve().parent.parent))
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from datetime import datetime, timedelta, timezone
from uuid import uuid4
from sqlalchemy import text
from app.database import SessionFactory

TENANT = "2857d0c5-6669-4d7d-a308-c8726bcc46bc"
USER = None  # resolved at runtime from DB (runs.user_id has FK to users)

async def main():
    global USER
    async with SessionFactory() as session:
        async with session.begin():
            row = (await session.execute(
                text("SELECT id FROM users WHERE tenant_id = :tid LIMIT 1"),
                {"tid": TENANT},
            )).mappings().first()
    if row is None:
        raise SystemExit(f"no user in tenant {TENANT} — cannot run recovery test")
    USER = str(row["id"])
    print(f"using user_id={USER}")

    run_id = uuid4()
    old_ts = datetime.now(timezone.utc) - timedelta(minutes=20)

    async with SessionFactory() as session:
        async with session.begin():
            await session.execute(
                text(
                    "INSERT INTO runs "
                    "(id, tenant_id, user_id, user_request, status, state_json, created_at) "
                    "VALUES (:id, :tid, :uid, 'test: recovery scan', 'failed', :state, :created)"
                ),
                {
                    "id": str(run_id), "tid": TENANT, "uid": USER,
                    "state": '{"partial": true, "completed_tasks": ["1"]}',
                    "created": old_ts,
                },
            )
    print(f"inserted failed run with state: {run_id}")

    from app.main import _recover_stuck_workflows
    await _recover_stuck_workflows()

    async with SessionFactory() as session:
        async with session.begin():
            audit = (await session.execute(
                text("SELECT event_type, payload FROM audit_events WHERE workflow_id = :wid"),
                {"wid": str(run_id)},
            )).mappings().all()

    print(f"audit rows: {[a['event_type'] for a in audit]}")
    assert any(a["event_type"] == "workflow.recoverable_on_boot" for a in audit), \
        "expected workflow.recoverable_on_boot audit row"

    print("\nPASS: recovery (runs table)")

asyncio.run(main())
