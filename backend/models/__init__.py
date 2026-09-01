"""
FINPATH Database Models

Exports all SQLAlchemy models for the FINPATH system.

Import Usage:
    from backend.models import User, Assessment, Prediction, Recommendation
"""

from backend.models.user import User
from backend.models.assessment import Assessment
from backend.models.prediction import Prediction
from backend.models.recommendation import Recommendation

__all__ = [
    "User",
    "Assessment",
    "Prediction",
    "Recommendation",
]
