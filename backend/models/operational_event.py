from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class OperationalEvent(Base):
	__tablename__ = "operational_events"

	id: Mapped[int] = mapped_column(primary_key=True)
	event_type: Mapped[str] = mapped_column(String(100), nullable=False)
	source: Mapped[str] = mapped_column(String(100), nullable=False)
	severity: Mapped[str] = mapped_column(String(20), nullable=False)
	summary: Mapped[str] = mapped_column(String(500), nullable=False)
	status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
	occurred_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), nullable=False,
		default=lambda: datetime.now(timezone.utc),
	)
	acknowledged_at: Mapped[datetime | None] = mapped_column(
		DateTime(timezone=True), nullable=True
	)
	acknowledged_by_user_id: Mapped[int | None] = mapped_column(
		Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
	)

	__table_args__ = (
		Index("ix_operational_events_occurred_at", "occurred_at"),
		Index("ix_operational_events_status_severity", "status", "severity"),
	)
