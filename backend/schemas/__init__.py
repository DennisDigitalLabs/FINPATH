from backend.schemas.assessment import AssessmentCreate, AssessmentResponse, AssessmentUpdate
from backend.schemas.dashboard import AnalyticsResponse, DashboardResponse, SystemAnalyticsResponse
from backend.schemas.prediction import PredictionCreate, PredictionRequest, PredictionResponse
from backend.schemas.recommendation import (
	RecommendationCreate,
	RecommendationResponse,
	RecommendationUpdate,
)
from backend.schemas.user import UserCreate, UserLogin, UserResponse, UserUpdate

__all__ = [
	"AssessmentCreate",
	"AssessmentResponse",
	"AssessmentUpdate",
	"AnalyticsResponse",
	"DashboardResponse",
	"PredictionCreate",
	"PredictionRequest",
	"PredictionResponse",
	"RecommendationCreate",
	"RecommendationResponse",
	"RecommendationUpdate",
	"SystemAnalyticsResponse",
	"UserCreate",
	"UserLogin",
	"UserResponse",
	"UserUpdate",
]
