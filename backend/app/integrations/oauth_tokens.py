"""Encrypted OAuth token storage.

Schema:
  integrations          — one row per (tenant, provider)
  integration_credentials — one encrypted JSON blob per integration

The blob holds:
  { access_token, refresh_token, expires_at, scopes, email }

encrypted_token is a Fernet-encrypted JSON string. The DB never holds
plaintext tokens.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any
from uuid import UUID

from cryptography.fernet import Fernet
from sqlalchemy import text

from app.config import settings
from app.database import SessionFactory


# ---------------------------------------------------------------- crypto


def _fernet() -> Fernet:
    key = settings.OAUTH_TOKEN_ENCRYPTION_KEY
    if not key:
        raise RuntimeError(
            "OAUTH_TOKEN_ENCRYPTION_KEY is not set. Generate one with: "
            'python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"'
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def _enc_json(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, default=_json_default).encode()
    return _fernet().encrypt(raw).decode()


def _dec_json(blob: str) -> dict[str, Any]:
    raw = _fernet().decrypt(blob.encode())
    return json.loads(raw.decode())


def _json_default(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"not JSON serializable: {type(obj).__name__}")


# --------------------------------------------------------- integrations


async def _find_integration_id(
    session, *, tenant_id: str, provider: str
) -> UUID | None:
    return (await session.execute(
        text(
            "SELECT id FROM integrations "
            "WHERE tenant_id = :tid AND provider = :prov "
            "ORDER BY connected_at DESC LIMIT 1"
        ),
        {"tid": tenant_id, "prov": provider},
    )).scalar()


async def _ensure_integration(
    session, *, tenant_id: str, provider: str, connected_by: str | None = None
) -> UUID:
    existing = await _find_integration_id(
        session, tenant_id=tenant_id, provider=provider
    )
    if existing:
        # Bump status if it was 'disconnected'
        await session.execute(
            text(
                "UPDATE integrations "
                "SET status = 'connected', connected_at = NOW() "
                "WHERE id = :id AND status <> 'connected'"
            ),
            {"id": existing},
        )
        return existing
    new_id = uuid4()
    await session.execute(
        text(
            "INSERT INTO integrations "
            "(id, tenant_id, provider, status, connected_by, connected_at) "
            "VALUES (:id, :tid, :prov, 'connected', :by, NOW())"
        ),
        {"id": new_id, "tid": tenant_id, "prov": provider, "by": connected_by},
    )
    return new_id


# ------------------------------------------------------------- public API


async def save_tokens(
    *,
    tenant_id: str | UUID,
    provider: str,
    access_token: str,
    refresh_token: str | None,
    expires_at: datetime | None,
    scopes: list[str] | None = None,
    account_email: str | None = None,
    connected_by: str | UUID | None = None,
) -> UUID:
    """Create/update integration + credentials. Returns the credentials id."""
    tid = str(tenant_id)
    payload = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "scopes": scopes or [],
        "email": account_email,
    }
    blob = _enc_json(payload)

    async with SessionFactory() as session:
        async with session.begin():
            iid = await _ensure_integration(
                session,
                tenant_id=tid,
                provider=provider,
                connected_by=str(connected_by) if connected_by else None,
            )

            existing = (await session.execute(
                text(
                    "SELECT id FROM integration_credentials "
                    "WHERE integration_id = :iid ORDER BY created_at DESC LIMIT 1"
                ),
                {"iid": iid},
            )).scalar()

            if existing:
                await session.execute(
                    text(
                        "UPDATE integration_credentials "
                        "SET encrypted_token = :blob, rotated_at = NOW() "
                        "WHERE id = :id"
                    ),
                    {"blob": blob, "id": existing},
                )
                return existing
            cred_id = uuid4()
            await session.execute(
                text(
                    "INSERT INTO integration_credentials "
                    "(id, integration_id, encrypted_token, created_at) "
                    "VALUES (:id, :iid, :blob, NOW())"
                ),
                {"id": cred_id, "iid": iid, "blob": blob},
            )
            return cred_id


async def load_tokens(
    *, tenant_id: str | UUID, provider: str
) -> dict[str, Any] | None:
    """Return decrypted payload dict, or None if not connected."""
    tid = str(tenant_id)
    async with SessionFactory() as session:
        async with session.begin():
            row = (await session.execute(
                text(
                    "SELECT c.encrypted_token "
                    "FROM integrations i "
                    "JOIN integration_credentials c ON c.integration_id = i.id "
                    "WHERE i.tenant_id = :tid AND i.provider = :prov "
                    "  AND i.status = 'connected' "
                    "ORDER BY c.created_at DESC LIMIT 1"
                ),
                {"tid": tid, "prov": provider},
            )).scalar()
    if row is None:
        return None
    return _dec_json(row)


async def rotate_access_token(
    *,
    tenant_id: str | UUID,
    provider: str,
    new_access_token: str,
    new_expires_at: datetime | None,
) -> bool:
    """Update only the access token + expiry, keep refresh_token unchanged."""
    current = await load_tokens(tenant_id=tenant_id, provider=provider)
    if current is None:
        return False
    current["access_token"] = new_access_token
    current["expires_at"] = new_expires_at.isoformat() if new_expires_at else None
    blob = _enc_json(current)

    tid = str(tenant_id)
    async with SessionFactory() as session:
        async with session.begin():
            result = await session.execute(
                text(
                    "UPDATE integration_credentials c "
                    "SET encrypted_token = :blob, rotated_at = NOW() "
                    "FROM integrations i "
                    "WHERE c.integration_id = i.id "
                    "  AND i.tenant_id = :tid AND i.provider = :prov"
                ),
                {"blob": blob, "tid": tid, "prov": provider},
            )
    return result.rowcount > 0


async def delete_tokens(*, tenant_id: str | UUID, provider: str) -> bool:
    """Delete integration (cascades to credentials if FK is ON DELETE CASCADE)."""
    tid = str(tenant_id)
    async with SessionFactory() as session:
        async with session.begin():
            result = await session.execute(
                text(
                    "DELETE FROM integrations "
                    "WHERE tenant_id = :tid AND provider = :prov"
                ),
                {"tid": tid, "prov": provider},
            )
    return result.rowcount > 0


# ----------------------------------------------------- CLI helper


if __name__ == "__main__":
    import asyncio, sys

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    async def _smoke():
        # Roundtrip a fake token for the given tenant
        tid = sys.argv[1] if len(sys.argv) > 1 else "2857d0c5-6669-4d7d-a308-c8726bcc46bc"
        await save_tokens(
            tenant_id=tid,
            provider="smoke-test",
            access_token="fake-access-xyz",
            refresh_token="fake-refresh-abc",
            expires_at=datetime.now(timezone.utc),
            scopes=["scope.one", "scope.two"],
            account_email="smoke@test.local",
        )
        loaded = await load_tokens(tenant_id=tid, provider="smoke-test")
        assert loaded and loaded["access_token"] == "fake-access-xyz", loaded
        assert loaded["refresh_token"] == "fake-refresh-abc", loaded
        assert loaded["email"] == "smoke@test.local", loaded
        await delete_tokens(tenant_id=tid, provider="smoke-test")
        print("PASS: oauth_tokens roundtrip (encrypt/decrypt/delete)")

    asyncio.run(_smoke())
