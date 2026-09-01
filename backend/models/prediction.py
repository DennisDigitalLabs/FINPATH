"""
FINPATH Prediction Model

Represents an ML-generated prediction for financial inclusion risk.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Integer, Float, ForeignKey, JSON, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.assessment import Assessment
    from backend.models.recommendation import Recommendation


class Prediction(Base):
    """
    Prediction model representing an ML prediction generated from an assessment.
    
    Attributes:
        id: Unique prediction identifier (primary key)
        assessment_id: Foreign key reference to Assessment
        risk_level: Risk level category (high, medium, low)
        risk_category: Specific risk category
        probability: Prediction probability/confidence (0-1)
        confidence: Additional confidence score if needed
        explanation: Human-readable explanation of the prediction
        contributing_factors: JSON structure of factors contributing to the prediction
        model_version: Version of the ML model used for prediction
        prediction_timestamp: Timestamp when the prediction was made
        created_at: Timestamp when the prediction record was created
    """
    
    __tablename__ = "predictions"
    
    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Foreign Keys
    assessment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Prediction Information
    risk_level: Mapped[str] = mapped_column(String(50), nullable=False)
    risk_category: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Prediction Scores
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=True)
    
    # Explanation & Contributing Factors
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    contributing_factors: Mapped[dict] = mapped_column(
        JSON,
        nullable=True,
        default=dict
    )
    
    # Model Metadata
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Prediction Timestamp
    prediction_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    
    # Record Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    assessment: Mapped["Assessment"] = relationship(
        "Assessment",
        back_populates="predictions",
        lazy="select"
    )
    
    recommendations: Mapped[list["Recommendation"]] = relationship(
        "Recommendation",
        back_populates="prediction",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    # Table configuration
    __table_args__ = (
        Index("ix_predictions_risk_level", "risk_level"),
        Index("ix_predictions_timestamp", "prediction_timestamp"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<Prediction(id={self.id}, assessment_id={self.assessment_id}, "
            f"risk_level={self.risk_level}, probability={self.probability})>"
        )
