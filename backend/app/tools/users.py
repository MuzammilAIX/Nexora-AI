"""User listing tool for bulk campaigns."""
from __future__ import annotations
import asyncio, sys
from sqlalchemy import text
from app.database import SessionFactory


def _ensure_windows_loop_policy():
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except Exception:
            pass


async def list_tenant_users(tenant_id: str) -> list[dict]:
    """Return all verified, non-deleted users for this tenant."""
    _ensure_windows_loop_policy()
    async with SessionFactory() as s:
        rows = (await s.execute(
            text(
                "SELECT id, email, role FROM users "
                "WHERE tenant_id = :t "
                "AND (deleted_at IS NULL) "
                "AND (email_verified = TRUE OR email_verified IS NULL) "
                "ORDER BY email"
            ),
            {"t": tenant_id},
        )).all()
    out = []
    for r in rows:
        email = r[1] or ""
        name = email.split("@")[0] if email else ""
        out.append({
            "id": str(r[0]),
            "email": email,
            "name": name.replace(".", " ").title(),
            "role": r[2] or "user",
        })
    return out


__all__ = ["list_tenant_users"]
