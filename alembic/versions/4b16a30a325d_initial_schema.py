"""initial_schema

Revision ID: 4b16a30a325d
Revises:
Create Date: 2026-08-31 20:58:42.394548

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "4b16a30a325d"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index("ix_users_is_active", "users", ["is_active"], unique=False)
    op.create_index("ix_users_role", "users", ["role"], unique=False)

    op.create_table(
        "assessments",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("assessment_status", sa.String(length=50), nullable=False, server_default="draft"),
        sa.Column("assessment_data", sa.JSON(), nullable=True),
        sa.Column("assessment_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_assessments_status", "assessments", ["assessment_status"], unique=False)
    op.create_index("ix_assessments_date", "assessments", ["assessment_date"], unique=False)
    op.create_index(op.f("ix_assessments_user_id"), "assessments", ["user_id"], unique=False)

    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("assessment_id", sa.Integer(), nullable=False),
        sa.Column("risk_level", sa.String(length=50), nullable=False),
        sa.Column("risk_category", sa.String(length=255), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("contributing_factors", sa.JSON(), nullable=True),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("prediction_timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_predictions_risk_level", "predictions", ["risk_level"], unique=False)
    op.create_index("ix_predictions_timestamp", "predictions", ["prediction_timestamp"], unique=False)
    op.create_index(op.f("ix_predictions_assessment_id"), "predictions", ["assessment_id"], unique=False)

    op.create_table(
        "recommendations",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("prediction_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("recommendation_text", sa.Text(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["prediction_id"], ["predictions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_recommendations_category", "recommendations", ["category"], unique=False)
    op.create_index("ix_recommendations_priority", "recommendations", ["priority"], unique=False)
    op.create_index(op.f("ix_recommendations_prediction_id"), "recommendations", ["prediction_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_recommendations_prediction_id"), table_name="recommendations")
    op.drop_index("ix_recommendations_priority", table_name="recommendations")
    op.drop_index("ix_recommendations_category", table_name="recommendations")
    op.drop_table("recommendations")

    op.drop_index(op.f("ix_predictions_assessment_id"), table_name="predictions")
    op.drop_index("ix_predictions_timestamp", table_name="predictions")
    op.drop_index("ix_predictions_risk_level", table_name="predictions")
    op.drop_table("predictions")

    op.drop_index(op.f("ix_assessments_user_id"), table_name="assessments")
    op.drop_index("ix_assessments_date", table_name="assessments")
    op.drop_index("ix_assessments_status", table_name="assessments")
    op.drop_table("assessments")

    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_is_active", table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
