from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class AdminAuditLog(Base):
	__tablename__ = "admin_audit_logs"

	id: Mapped[int] = mapped_column(primary_key=True)
	actor_user_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
	)
	action: Mapped[str] = mapped_column(String(100), nullable=False)
	target_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
	target_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
	outcome: Mapped[str] = mapped_column(
		String(20), nullable=False, default="unknown", server_default="unknown"
	)
	details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), nullable=False,
		default=lambda: datetime.now(timezone.utc),
	)

	__table_args__ = (
		Index("ix_admin_audit_logs_created_at", "created_at"),
		Index("ix_admin_audit_logs_action_created_at", "action", "created_at"),
		Index("ix_admin_audit_logs_outcome_created_at", "outcome", "created_at"),
	)
