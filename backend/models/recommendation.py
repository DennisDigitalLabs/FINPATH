"""
FINPATH Recommendation Model

Represents personalized financial inclusion recommendations.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Integer, ForeignKey, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.prediction import Prediction


class Recommendation(Base):
    """
    Recommendation model representing personalized financial inclusion recommendations.
    
    Attributes:
        id: Unique recommendation identifier (primary key)
        prediction_id: Foreign key reference to Prediction
        category: Recommendation category (e.g., financial_product, intervention, support_service)
        recommendation_text: Detailed recommendation text
        priority: Priority level (1=highest, 5=lowest)
        created_at: Timestamp when the recommendation was created
    """
    
    __tablename__ = "recommendations"
    
    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Foreign Keys
    prediction_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("predictions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Recommendation Information
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    recommendation_text: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Priority (1=highest, 5=lowest)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    
    # Record Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    prediction: Mapped["Prediction"] = relationship(
        "Prediction",
        back_populates="recommendations",
        lazy="select"
    )
    
    # Table configuration
    __table_args__ = (
        Index("ix_recommendations_category", "category"),
        Index("ix_recommendations_priority", "priority"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<Recommendation(id={self.id}, prediction_id={self.prediction_id}, "
            f"category={self.category}, priority={self.priority})>"
        )
