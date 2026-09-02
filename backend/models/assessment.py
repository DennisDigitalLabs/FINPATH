"""
FINPATH Assessment Model

Represents a financial inclusion assessment taken by a user.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Integer, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.user import User
    from backend.models.prediction import Prediction


class Assessment(Base):
    """
    Assessment model representing a user's financial inclusion assessment.
    
    Attributes:
        id: Unique assessment identifier (primary key)
        user_id: Foreign key reference to User
        assessment_status: Status of the assessment (draft, submitted, completed)
        assessment_data: Structured assessment/input data (JSON)
        assessment_date: Date and time when the assessment was conducted
        created_at: Timestamp when the assessment record was created
        updated_at: Timestamp when the assessment record was last updated
    """
    
    __tablename__ = "assessments"
    
    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Foreign Keys
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Assessment Information
    assessment_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="draft"
    )
    
    # Structured assessment data (JSON for flexibility with Yvette's features)
    assessment_data: Mapped[dict] = mapped_column(
        JSON,
        nullable=True,
        default=dict
    )
    
    # Assessment Timestamp
    assessment_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    
    # Record Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="assessments",
        lazy="select"
    )
    
    predictions: Mapped[list["Prediction"]] = relationship(
        "Prediction",
        back_populates="assessment",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    # Table configuration
    __table_args__ = (
        Index("ix_assessments_status", "assessment_status"),
        Index("ix_assessments_date", "assessment_date"),
    )
    
    def __repr__(self) -> str:
        return f"<Assessment(id={self.id}, user_id={self.user_id}, status={self.assessment_status})>"
