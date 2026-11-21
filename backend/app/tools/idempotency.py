"""
Idempotency key management (Section 7.5: "avoid duplicate external actions").

Design:
  - One row per (key). Unique constraint prevents races.
  - status: in_flight -> succeeded | failed
  - check_or_mark returns:
      True  -> fresh action, caller may proceed
      False -> action already succeeded, caller must SKIP
      raises IdempotencyConflict -> another worker holds the lock
"""
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from ..database import SessionFactory
from .audit import log_event


class IdempotencyConflict(RuntimeError):
    """Raised when an action with the same key is already in-flight."""


async def check_or_mark(
    idempotency_key: str,
    tenant_id: str,
    action_type: str,
) -> bool:
    """
    Returns True if caller should proceed.
    Returns False if the action already succeeded (skip).
    Raises IdempotencyConflict if another worker is mid-action.
    """
    async with SessionFactory() as session:
        async with session.begin():
            try:
                await session.execute(
                    text(
                        "INSERT INTO idempotency_keys "
                        "(key, tenant_id, action_type, status) "
                        "VALUES (:key, :tid, :atype, 'in_flight')"
                    ),
                    {"key": idempotency_key, "tid": tenant_id, "atype": action_type},
                )
                await log_event(
                    tenant_id=tenant_id,
                    event_type="idempotency.fresh",
                    payload={"key": idempotency_key, "action_type": action_type},
                )
                return True
            except IntegrityError:
                pass

    async with SessionFactory() as session:
        async with session.begin():
            row = (
                await session.execute(
                    text(
                        "SELECT status, tenant_id, action_type "
                        "FROM idempotency_keys WHERE key = :key"
                    ),
                    {"key": idempotency_key},
                )
            ).mappings().first()

    if row is None:
        return True

    if row["status"] == "succeeded":
        await log_event(
            tenant_id=tenant_id,
            event_type="idempotency.hit",
            payload={"key": idempotency_key, "action_type": action_type},
        )
        return False

    if row["status"] == "failed":
        async with SessionFactory() as session:
            async with session.begin():
                await session.execute(
                    text(
                        "UPDATE idempotency_keys "
                        "SET status='in_flight', error=NULL, completed_at=NULL "
                        "WHERE key = :key"
                    ),
                    {"key": idempotency_key},
                )
        await log_event(
            tenant_id=tenant_id,
            event_type="idempotency.retry",
            payload={"key": idempotency_key, "action_type": action_type},
        )
        return True

    raise IdempotencyConflict(
        f"Action '{idempotency_key}' is already in-flight "
        f"(tenant={tenant_id}, type={action_type})"
    )


async def mark_succeeded(idempotency_key: str, tenant_id: str) -> None:
    async with SessionFactory() as session:
        async with session.begin():
            await session.execute(
                text(
                    "UPDATE idempotency_keys "
                    "SET status='succeeded', completed_at=NOW() "
                    "WHERE key = :key"
                ),
                {"key": idempotency_key},
            )
    await log_event(
        tenant_id=tenant_id,
        event_type="idempotency.succeeded",
        payload={"key": idempotency_key},
    )


async def mark_failed(idempotency_key: str, tenant_id: str, error: str) -> None:
    async with SessionFactory() as session:
        async with session.begin():
            await session.execute(
                text(
                    "UPDATE idempotency_keys "
                    "SET status='failed', error=:err, completed_at=NOW() "
                    "WHERE key = :key"
                ),
                {"key": idempotency_key, "err": error[:1000]},
            )
    await log_event(
        tenant_id=tenant_id,
        event_type="idempotency.failed",
        payload={"key": idempotency_key, "error": error[:1000]},
    )
