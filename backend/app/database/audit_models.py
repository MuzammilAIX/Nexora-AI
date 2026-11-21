from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from . import Base


class AuditEvent(Base):
    """
    Append-only audit log. No update path. No delete route.
    Every row records: who did what, to which subject, with what payload.
    """
    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    subject_type: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    subject_id: Mapped[str] = mapped_column(String(128), nullable=False, default="", index=True)
    run_id: Mapped[UUID | None] = mapped_column(
        # NOT a ForeignKey: audit_events is append-only and must not be
        # constrained by mutable operational tables (Section 9). Join by
        # UUID at query time if referential integrity is needed.
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
