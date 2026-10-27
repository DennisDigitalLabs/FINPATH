"""add explicit outcome to admin audit records

Revision ID: e31c9b6a48d2
Revises: d8a4c7f19b32
"""

from alembic import op
import sqlalchemy as sa


revision = "e31c9b6a48d2"
down_revision = "d8a4c7f19b32"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "admin_audit_logs",
        sa.Column(
            "outcome",
            sa.String(length=20),
            nullable=False,
            server_default="unknown",
        ),
    )
    op.create_index(
        "ix_admin_audit_logs_outcome_created_at",
        "admin_audit_logs",
        ["outcome", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_admin_audit_logs_outcome_created_at",
        table_name="admin_audit_logs",
    )
    op.drop_column("admin_audit_logs", "outcome")
