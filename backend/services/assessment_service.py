from sqlalchemy.orm import Session

from backend.models import Assessment, User
from backend.schemas.assessment import AssessmentCreate, AssessmentUpdate


def list_user_assessments(db: Session, user: User) -> list[Assessment]:
	return (
		db.query(Assessment)
		.filter(Assessment.user_id == user.id)
		.order_by(Assessment.created_at.desc())
		.all()
	)


def get_user_assessment(db: Session, assessment_id: int, user: User) -> Assessment | None:
	return (
		db.query(Assessment)
		.filter(Assessment.id == assessment_id, Assessment.user_id == user.id)
		.first()
	)


def create_assessment(db: Session, user: User, data: AssessmentCreate) -> Assessment:
	values = data.model_dump(exclude_none=True)
	assessment = Assessment(user_id=user.id, **values)
	db.add(assessment)
	db.commit()
	db.refresh(assessment)
	return assessment


def update_assessment(
	db: Session, assessment: Assessment, data: AssessmentUpdate
) -> Assessment:
	for field, value in data.model_dump(exclude_unset=True).items():
		setattr(assessment, field, value)
	db.commit()
	db.refresh(assessment)
	return assessment


def delete_assessment(db: Session, assessment: Assessment) -> None:
	db.delete(assessment)
	db.commit()
