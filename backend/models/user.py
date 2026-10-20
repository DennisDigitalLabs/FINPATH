"""
FINPATH User Model

Represents a user in the financial inclusion assessment system.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.assessment import Assessment


class User(Base):
    """
    User model representing a system user.
    
    Attributes:
        id: Unique user identifier (primary key)
        full_name: User's full name
        email: User's email address (unique)
        hashed_password: Securely hashed password (never stored in plaintext)
        role: User role (user, admin)
        is_active: Whether the user account is active
        created_at: Timestamp when the user was created
        updated_at: Timestamp when the user was last updated
    """
    
    __tablename__ = "users"
    
    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # User Information
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # User Status
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    # Timestamps
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
    assessments: Mapped[list["Assessment"]] = relationship(
        "Assessment",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    # Table configuration
    __table_args__ = (
        Index("ix_users_is_active", "is_active"),
        Index("ix_users_role", "role"),
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
