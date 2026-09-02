from sqlalchemy.orm import Session

from backend.models import Assessment, Prediction, Recommendation, User
from backend.schemas.recommendation import RecommendationCreate, RecommendationUpdate


def list_user_recommendations(db: Session, user: User) -> list[Recommendation]:
	return (
		db.query(Recommendation)
		.join(Prediction, Recommendation.prediction_id == Prediction.id)
		.join(Assessment, Prediction.assessment_id == Assessment.id)
		.filter(Assessment.user_id == user.id)
		.order_by(Recommendation.priority.asc(), Recommendation.created_at.desc())
		.all()
	)


def get_user_recommendation(
	db: Session, recommendation_id: int, user: User
) -> Recommendation | None:
	return (
		db.query(Recommendation)
		.join(Prediction, Recommendation.prediction_id == Prediction.id)
		.join(Assessment, Prediction.assessment_id == Assessment.id)
		.filter(
			Recommendation.id == recommendation_id,
			Assessment.user_id == user.id,
		)
		.first()
	)


def create_recommendation(
	db: Session, prediction: Prediction, data: RecommendationCreate
) -> Recommendation:
	"""Create a record from a trusted recommendation generator."""
	if data.prediction_id != prediction.id:
		raise ValueError("Recommendation output does not match the prediction")
	recommendation = Recommendation(
		prediction_id=prediction.id,
		category=data.category,
		recommendation_text=data.recommendation_text,
		priority=data.priority,
	)
	db.add(recommendation)
	db.commit()
	db.refresh(recommendation)
	return recommendation


def update_recommendation(
	db: Session, recommendation: Recommendation, data: RecommendationUpdate
) -> Recommendation:
	for field, value in data.model_dump(exclude_unset=True).items():
		setattr(recommendation, field, value)
	db.commit()
	db.refresh(recommendation)
	return recommendation
