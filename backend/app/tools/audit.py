"""
Append-only audit log (Section 9: "Keep audit events append-only").

Never update or delete. Insert only.

Failures in this module are swallowed so a logging problem never breaks
a workflow. Traceback goes to stderr for visibility.
"""
from typing import Any
from sqlalchemy import text
from ..database import SessionFactory

# Default subject_type per event_type prefix. Keeps existing call sites
# (retry.py, idempotency.py, main.py recovery) working without changes.
_SUBJECT_TYPE_MAP = {
    "retry": "workflow",
    "idempotency": "action",
    "workflow": "workflow",
    "agent": "workflow",
    "approval": "workflow",
    "integration": "integration",
    "auth": "user",
}


def _derive_subject_type(event_type: str) -> str:
    prefix = event_type.split(".", 1)[0].lower()
    return _SUBJECT_TYPE_MAP.get(prefix, "system")


async def log_event(
    tenant_id: str | None,
    event_type: str,
    payload: dict[str, Any] | None = None,
    workflow_id: str | None = None,
    task_id: str | None = None,
    subject_type: str | None = None,
    subject_id: str | None = None,
) -> None:
    """
    Append a single audit event. Fire-and-forget friendly.

    subject_type / subject_id default from event_type and workflow_id
    if not supplied, so legacy call sites keep working.
    """
    resolved_subject_type = subject_type or _derive_subject_type(event_type)
    resolved_subject_id = subject_id or workflow_id or task_id or "unknown"

    try:
        async with SessionFactory() as session:
            async with session.begin():
                await session.execute(
                    text(
                        "INSERT INTO audit_events "
                        "(tenant_id, event_type, subject_type, subject_id, "
                        " workflow_id, task_id, payload, created_at) "
                        "VALUES (:tid, :etype, :stype, :sid, "
                        " :wid, :tid2, CAST(:payload AS jsonb), NOW())"
                    ),
                    {
                        "tid": tenant_id,
                        "etype": event_type,
                        "stype": resolved_subject_type,
                        "sid": resolved_subject_id,
                        "wid": workflow_id,
                        "tid2": task_id,
                        "payload": _json_dumps(payload or {}),
                    },
                )
    except Exception:
        import traceback
        traceback.print_exc()


def _json_dumps(obj: Any) -> str:
    import json
    return json.dumps(obj, default=str)
