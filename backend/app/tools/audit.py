"""
Append-only audit log. Insert-only. Failures never break a workflow.
"""
import json
from typing import Any
from uuid import UUID

from sqlalchemy import text

from ..database import SessionFactory


_SUBJECT_TYPE_MAP = {
    "retry": "workflow",
    "idempotency": "action",
    "workflow": "workflow",
    "agent": "workflow",
    "approval": "workflow",
    "integration": "integration",
    "auth": "user",
    "team": "user",
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
    *,
    actor_user_id: UUID | str | None = None,
    actor_type: str = "user",
    actor_label: str | None = None,
    severity: str = "info",
    correlation_id: UUID | str | None = None,
    before_state: dict | None = None,
    after_state: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """
    Append a single audit event. Fire-and-forget.

    Backward compatible with earlier call sites: subject_type/subject_id
    default from event_type and workflow_id if not supplied.
    """
    if not tenant_id:
        return

    resolved_subject_type = subject_type or _derive_subject_type(event_type)
    resolved_subject_id = subject_id or workflow_id or task_id or "unknown"

    try:
        async with SessionFactory() as session:
            async with session.begin():
                await session.execute(
                    text(
                        "INSERT INTO audit_events "
                        "(tenant_id, actor_user_id, actor_type, actor_label, "
                        " event_type, subject_type, subject_id, run_id, "
                        " workflow_id, task_id, payload, before_state, after_state, "
                        " severity, correlation_id, ip_address, user_agent, created_at) "
                        "VALUES ("
                        " :tid, :auid, :atype, :alabel,"
                        " :etype, :stype, :sid, NULL,"
                        " :wid, :task, CAST(:payload AS json),"
                        " CAST(:before AS jsonb), CAST(:after AS jsonb),"
                        " :sev, :cid, :ip, :ua, NOW())"
                    ),
                    {
                        "tid": tenant_id,
                        "auid": str(actor_user_id) if actor_user_id else None,
                        "atype": actor_type,
                        "alabel": actor_label,
                        "etype": event_type,
                        "stype": resolved_subject_type,
                        "sid": resolved_subject_id,
                        "wid": workflow_id,
                        "task": task_id,
                        "payload": _json_dumps(payload or {}),
                        "before": _json_dumps(before_state) if before_state else None,
                        "after": _json_dumps(after_state) if after_state else None,
                        "sev": severity,
                        "cid": str(correlation_id) if correlation_id else None,
                        "ip": ip_address,
                        "ua": user_agent,
                    },
                )
    except Exception:
        import traceback
        traceback.print_exc()


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, default=str)
