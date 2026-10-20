from sqlalchemy.orm import Session

from backend.models import Assessment, Prediction, Recommendation, User
from backend.schemas.dashboard import DashboardResponse


def get_user_dashboard(db: Session, user: User) -> DashboardResponse:
    assessments = (
        db.query(Assessment)
        .filter(Assessment.user_id == user.id)
        .order_by(Assessment.created_at.desc())
        .all()
    )
    latest_assessment = assessments[0] if assessments else None
    latest_prediction = None
    latest_recommendations: list[Recommendation] = []

    if latest_assessment is not None:
        latest_prediction = (
            db.query(Prediction)
            .filter(Prediction.assessment_id == latest_assessment.id)
            .order_by(Prediction.created_at.desc())
            .first()
        )
        if latest_prediction is not None:
            latest_recommendations = (
                db.query(Recommendation)
                .filter(Recommendation.prediction_id == latest_prediction.id)
                .order_by(Recommendation.priority.asc(), Recommendation.created_at.desc())
                .all()
            )

    recent_activity = [
        {
            "assessment_id": assessment.id,
            "assessment_status": assessment.assessment_status,
            "assessment_date": assessment.assessment_date,
            "has_prediction": bool(assessment.predictions),
        }
        for assessment in assessments[:10]
    ]
    return DashboardResponse(
        user=user,
        assessment_count=len(assessments),
        latest_assessment=latest_assessment,
        latest_prediction=latest_prediction,
        latest_recommendations=latest_recommendations,
        recent_activity=recent_activity,
    )
