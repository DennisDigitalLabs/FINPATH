"""add durable admin audit and operational events

Revision ID: d8a4c7f19b32
Revises: a3c9d7e42f61
"""

from alembic import op
import sqlalchemy as sa


revision = "d8a4c7f19b32"
down_revision = "a3c9d7e42f61"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("target_type", sa.String(length=100), nullable=True),
        sa.Column("target_id", sa.String(length=100), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_admin_audit_logs_created_at", "admin_audit_logs", ["created_at"]
    )
    op.create_index(
        "ix_admin_audit_logs_action_created_at",
        "admin_audit_logs",
        ["action", "created_at"],
    )
    op.create_table(
        "operational_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["acknowledged_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_operational_events_occurred_at", "operational_events", ["occurred_at"]
    )
    op.create_index(
        "ix_operational_events_status_severity",
        "operational_events",
        ["status", "severity"],
    )


def downgrade() -> None:
    op.drop_index("ix_operational_events_status_severity", table_name="operational_events")
    op.drop_index("ix_operational_events_occurred_at", table_name="operational_events")
    op.drop_table("operational_events")
    op.drop_index(
        "ix_admin_audit_logs_action_created_at", table_name="admin_audit_logs"
    )
    op.drop_index("ix_admin_audit_logs_created_at", table_name="admin_audit_logs")
    op.drop_table("admin_audit_logs")
