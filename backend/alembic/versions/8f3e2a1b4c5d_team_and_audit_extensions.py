"""team and audit extensions

Revision ID: 8f3e2a1b4c5d
Revises: 93d228bbd245
Create Date: 2026-11-22 14:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import json

revision = "8f3e2a1b4c5d"
down_revision = "93d228bbd245"
branch_labels = None
depends_on = None


SYSTEM_ROLES = [
    ("owner", "Full control including billing and org deletion", {
        "manage_members": True, "manage_integrations": True,
        "configure_agents": True, "create_workflows": True,
        "execute_workflows": True, "approve_actions": True,
        "view_analytics": True, "manage_billing": True,
        "allowed_agents": ["orchestrator","support","sales","analytics","operations"],
    }),
    ("admin", "Administrative access, no billing", {
        "manage_members": True, "manage_integrations": True,
        "configure_agents": True, "create_workflows": True,
        "execute_workflows": True, "approve_actions": True,
        "view_analytics": True, "manage_billing": False,
        "allowed_agents": ["orchestrator","support","sales","analytics","operations"],
    }),
    ("manager", "Creates workflows, approves actions", {
        "manage_members": False, "manage_integrations": False,
        "configure_agents": False, "create_workflows": True,
        "execute_workflows": True, "approve_actions": True,
        "view_analytics": True, "manage_billing": False,
        "allowed_agents": ["orchestrator","support","sales","analytics","operations"],
    }),
    ("operator", "Executes assigned workflows", {
        "manage_members": False, "manage_integrations": False,
        "configure_agents": False, "create_workflows": False,
        "execute_workflows": True, "approve_actions": False,
        "view_analytics": True, "manage_billing": False,
        "allowed_agents": ["orchestrator","support","sales"],
    }),
    ("viewer", "Read-only", {
        "manage_members": False, "manage_integrations": False,
        "configure_agents": False, "create_workflows": False,
        "execute_workflows": False, "approve_actions": False,
        "view_analytics": True, "manage_billing": False,
        "allowed_agents": ["orchestrator"],
    }),
]


def upgrade() -> None:
    # ---- 1. Extend audit_events
    op.execute("""
        ALTER TABLE audit_events
          ADD COLUMN IF NOT EXISTS actor_type VARCHAR(16) NOT NULL DEFAULT 'user',
          ADD COLUMN IF NOT EXISTS actor_label VARCHAR(255) NULL,
          ADD COLUMN IF NOT EXISTS severity VARCHAR(16) NOT NULL DEFAULT 'info',
          ADD COLUMN IF NOT EXISTS correlation_id UUID NULL,
          ADD COLUMN IF NOT EXISTS ip_address VARCHAR(45) NULL,
          ADD COLUMN IF NOT EXISTS user_agent TEXT NULL,
          ADD COLUMN IF NOT EXISTS before_state JSONB NULL,
          ADD COLUMN IF NOT EXISTS after_state JSONB NULL
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_audit_events_correlation_id
        ON audit_events(correlation_id)
    """)

    # ---- 2. Create roles table
    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("permissions", postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_role_tenant_name"),
    )
    op.create_index("ix_roles_tenant_id", "roles", ["tenant_id"])

    # ---- 3. Extend users
    op.execute("""
        ALTER TABLE users
          ADD COLUMN IF NOT EXISTS status VARCHAR(16) NOT NULL DEFAULT 'active',
          ADD COLUMN IF NOT EXISTS role_id UUID NULL,
          ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ NULL,
          ADD COLUMN IF NOT EXISTS two_factor_enabled BOOLEAN NOT NULL DEFAULT false,
          ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ NULL
    """)
    op.execute("""
        ALTER TABLE users
          ADD CONSTRAINT fk_users_role_id
          FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE SET NULL
    """)
    op.create_index("ix_users_role_id", "users", ["role_id"])

    # ---- 4. Create invitations table
    op.create_table(
        "invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("invited_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_invitations_tenant_id", "invitations", ["tenant_id"])
    op.create_index("ix_invitations_email", "invitations", ["email"])

    # ---- 5. Seed system roles
    values_sql = ",\n".join(
        "(" + ", ".join([
            "gen_random_uuid()",
            "NULL",
            "'" + name.replace("'", "''") + "'",
            "'" + desc.replace("'", "''") + "'",
            "true",
            "$$" + json.dumps(perms) + "$$::jsonb",
        ]) + ")"
        for name, desc, perms in SYSTEM_ROLES
    )
    op.execute(f"""
        INSERT INTO roles (id, tenant_id, name, description, is_system, permissions)
        VALUES {values_sql}
    """)

    # ---- 6. Backfill existing users' role_id
    op.execute("""
        UPDATE users u
        SET role_id = r.id
        FROM roles r
        WHERE r.is_system = true
          AND r.name = CASE
            WHEN u.role IN ('owner','admin','manager','operator','viewer') THEN u.role
            WHEN u.role = 'member' THEN 'viewer'
            ELSE 'viewer'
          END
          AND u.role_id IS NULL
    """)


def downgrade() -> None:
    op.drop_index("ix_invitations_email", table_name="invitations")
    op.drop_index("ix_invitations_tenant_id", table_name="invitations")
    op.drop_table("invitations")

    op.drop_index("ix_users_role_id", table_name="users")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS fk_users_role_id")
    op.execute("""
        ALTER TABLE users
          DROP COLUMN IF EXISTS status,
          DROP COLUMN IF EXISTS role_id,
          DROP COLUMN IF EXISTS last_login_at,
          DROP COLUMN IF EXISTS two_factor_enabled,
          DROP COLUMN IF EXISTS deleted_at
    """)

    op.drop_index("ix_roles_tenant_id", table_name="roles")
    op.drop_table("roles")

    op.execute("DROP INDEX IF EXISTS ix_audit_events_correlation_id")
    op.execute("""
        ALTER TABLE audit_events
          DROP COLUMN IF EXISTS actor_type,
          DROP COLUMN IF EXISTS actor_label,
          DROP COLUMN IF EXISTS severity,
          DROP COLUMN IF EXISTS correlation_id,
          DROP COLUMN IF EXISTS ip_address,
          DROP COLUMN IF EXISTS user_agent,
          DROP COLUMN IF EXISTS before_state,
          DROP COLUMN IF EXISTS after_state
    """)
