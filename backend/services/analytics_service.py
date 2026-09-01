from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Query, Session

from backend.models import Assessment, Prediction, Recommendation, User
from backend.schemas.dashboard import AnalyticsResponse, SystemAnalyticsResponse


def _analytics_for_query(
	assessment_query: Query, prediction_query: Query, recommendation_query: Query
) -> AnalyticsResponse:
	status_rows = assessment_query.with_entities(
		Assessment.assessment_status, func.count(Assessment.id)
	).group_by(Assessment.assessment_status).all()
	risk_rows = prediction_query.with_entities(
		Prediction.risk_level, func.count(Prediction.id)
	).group_by(Prediction.risk_level).all()
	total = assessment_query.with_entities(func.count(Assessment.id)).scalar() or 0
	completed = assessment_query.filter(Assessment.assessment_status == "completed").count()
	predictions = prediction_query.with_entities(func.count(Prediction.id)).scalar() or 0
	recommendations = recommendation_query.with_entities(
		func.count(Recommendation.id)
	).scalar() or 0
	return AnalyticsResponse(
		total_assessments=total,
		completed_assessments=completed,
		assessment_status_distribution={status: count for status, count in status_rows},
		prediction_count=predictions,
		risk_level_distribution={level: count for level, count in risk_rows},
		recommendation_count=recommendations,
	)


def get_user_analytics(db: Session, user: User) -> AnalyticsResponse:
	assessments = db.query(Assessment).filter(Assessment.user_id == user.id)
	predictions = (
		db.query(Prediction)
		.join(Assessment, Prediction.assessment_id == Assessment.id)
		.filter(Assessment.user_id == user.id)
	)
	recommendations = (
		db.query(Recommendation)
		.join(Prediction, Recommendation.prediction_id == Prediction.id)
		.join(Assessment, Prediction.assessment_id == Assessment.id)
		.filter(Assessment.user_id == user.id)
	)
	return _analytics_for_query(assessments, predictions, recommendations)


def get_system_analytics(db: Session) -> SystemAnalyticsResponse:
	analytics = _analytics_for_query(
		db.query(Assessment), db.query(Prediction), db.query(Recommendation)
	)
	return SystemAnalyticsResponse(
		**analytics.model_dump(),
		user_count=db.query(func.count(User.id)).scalar() or 0,
		active_user_count=db.query(User).filter(User.is_active.is_(True)).count(),
		generated_at=datetime.now(timezone.utc),
	)
