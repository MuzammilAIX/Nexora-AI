"""
Append-only audit log writer.

Every call inserts one row. Never update, never delete. Failures are
logged but never raised — auditing must not break the business path.
"""
import logging
from uuid import UUID

from .database import SessionFactory
from .database.audit_models import AuditEvent


log = logging.getLogger(__name__)


async def audit(
    *,
    tenant_id: str | UUID | None,
    actor_user_id: str | UUID | None,
    event_type: str,
    subject_type: str = "",
    subject_id: str = "",
    run_id: str | UUID | None = None,
    payload: dict | None = None,
) -> None:
    if not tenant_id:
        log.warning("audit: skipping event %s — no tenant_id", event_type)
        return

    def _uuid(v):
        if v is None or v == "":
            return None
        try:
            return UUID(str(v))
        except (ValueError, AttributeError):
            return None

    try:
        async with SessionFactory() as db:
            row = AuditEvent(
                tenant_id=_uuid(tenant_id),
                actor_user_id=_uuid(actor_user_id),
                event_type=event_type,
                subject_type=subject_type,
                subject_id=str(subject_id or ""),
                run_id=_uuid(run_id),
                payload=payload or {},
            )
            db.add(row)
            await db.commit()
    except Exception as exc:
        log.error("audit write failed for %s: %s", event_type, exc)
