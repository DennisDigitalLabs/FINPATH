"""add per-user access token version

Revision ID: f4a12d9c6e83
Revises: e31c9b6a48d2
"""

from alembic import op
import sqlalchemy as sa


revision = "f4a12d9c6e83"
down_revision = "e31c9b6a48d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("users", "token_version")
