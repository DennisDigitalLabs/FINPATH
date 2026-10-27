from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from backend.schemas.assessment import AssessmentResponse
from backend.schemas.prediction import PredictionResponse
from backend.schemas.recommendation import RecommendationResponse
from backend.schemas.user import UserResponse


class DashboardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user: UserResponse
    assessment_count: int
    latest_assessment: AssessmentResponse | None = None
    latest_prediction: PredictionResponse | None = None
    latest_recommendations: list[RecommendationResponse]
    recent_activity: list[dict[str, Any]]


class AnalyticsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_assessments: int
    completed_assessments: int
    assessment_status_distribution: dict[str, int]
    prediction_count: int
    risk_level_distribution: dict[str, int]
    recommendation_count: int


class SystemAnalyticsResponse(AnalyticsResponse):
    user_count: int
    active_user_count: int
    generated_at: datetime
    assessment_completion_rate: float | None
    risk_category_distribution: dict[str, int]