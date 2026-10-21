"""add per-user assessment idempotency keys

Revision ID: a3c9d7e42f61
Revises: 7f2c1d9a6b4e
"""

from alembic import op
import sqlalchemy as sa


revision = "a3c9d7e42f61"
down_revision = "7f2c1d9a6b4e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assessments", sa.Column("idempotency_key", sa.String(length=36), nullable=True))
    op.create_index(
        "uq_assessments_user_idempotency_key",
        "assessments",
        ["user_id", "idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_assessments_user_idempotency_key", table_name="assessments")
    op.drop_column("assessments", "idempotency_key")
