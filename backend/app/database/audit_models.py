from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
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
    actor_type: Mapped[str] = mapped_column(
        String(16), nullable=False, default="user"
    )
    actor_label: Mapped[str | None] = mapped_column(String(255), nullable=True)

    event_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    subject_type: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    subject_id: Mapped[str] = mapped_column(
        String(128), nullable=False, default="", index=True
    )
    run_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True, index=True
    )
    # Legacy text columns used by tools/audit.py raw INSERT path.
    workflow_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    before_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    severity: Mapped[str] = mapped_column(
        String(16), nullable=False, default="info"
    )
    correlation_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True, index=True
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
