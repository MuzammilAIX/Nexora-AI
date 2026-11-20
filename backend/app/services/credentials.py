"""
Tenant-scoped credential resolver.

Looks up an integration credential for a specific tenant:
  integrations (tenant_id + provider) -> integration_credentials (latest) -> decrypt.

Falls back to settings.HUBSPOT_ACCESS_TOKEN ONLY when settings.DEBUG is True,
so production tenants must connect their own HubSpot. Every other tenant gets
a clear "no integration connected" error.
"""
import logging
from uuid import UUID

from sqlalchemy import select

from ..config import settings
from ..crypto import decrypt_token
from ..database import SessionFactory
from ..database.integration_models import (
    Integration,
    IntegrationCredential,
)


log = logging.getLogger(__name__)


class IntegrationNotConnected(RuntimeError):
    """Raised when a tenant has no credential for the requested provider."""


async def get_hubspot_token(tenant_id: str | UUID | None) -> str:
    """
    Return a decrypted HubSpot token for this tenant.

    Raises IntegrationNotConnected if:
      - tenant_id is missing/blank, OR
      - no integration row exists for this tenant + 'hubspot', OR
      - integration has no credential, OR
      - decryption fails.

    The only path that bypasses all of that is settings.DEBUG=True AND the
    global settings.HUBSPOT_ACCESS_TOKEN is non-empty — used for local dev
    smoke tests where wiring a full integration row is overkill.
    """
    if tenant_id:
        try:
            tenant_uuid = UUID(str(tenant_id))
        except (ValueError, AttributeError):
            tenant_uuid = None

        if tenant_uuid is not None:
            try:
                async with SessionFactory() as db:
                    integ_stmt = (
                        select(Integration)
                        .where(Integration.tenant_id == tenant_uuid)
                        .where(Integration.provider == "hubspot")
                        .limit(1)
                    )
                    integration = (
                        await db.execute(integ_stmt)
                    ).scalar_one_or_none()

                    if integration is not None:
                        cred_stmt = (
                            select(IntegrationCredential)
                            .where(
                                IntegrationCredential.integration_id
                                == integration.id
                            )
                            .order_by(IntegrationCredential.created_at.desc())
                            .limit(1)
                        )
                        cred = (
                            await db.execute(cred_stmt)
                        ).scalar_one_or_none()

                        if cred is not None and cred.encrypted_token:
                            try:
                                return decrypt_token(cred.encrypted_token)
                            except Exception as exc:
                                log.error(
                                    "decrypt failed for tenant %s integration %s: %s",
                                    tenant_uuid, integration.id, exc,
                                )
            except Exception as exc:
                log.error(
                    "credential lookup failed for tenant %s: %s",
                    tenant_uuid, exc,
                )

    # Dev-only fallback. Production tenants with no integration row get the
    # exception below, which the LeadAgent surfaces as a clear error.
    if settings.DEBUG and settings.HUBSPOT_ACCESS_TOKEN:
        log.warning(
            "using settings.HUBSPOT_ACCESS_TOKEN fallback (DEBUG mode, "
            "tenant=%s has no connected HubSpot integration)",
            tenant_id,
        )
        return settings.HUBSPOT_ACCESS_TOKEN

    raise IntegrationNotConnected(
        "No HubSpot integration is connected for this tenant. "
        "Ask an admin to connect HubSpot in Settings > Integrations."
    )
