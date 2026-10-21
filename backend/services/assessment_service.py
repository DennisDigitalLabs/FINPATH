from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import Assessment, User
from backend.schemas.assessment import AssessmentCreate, AssessmentUpdate


class AssessmentIdempotencyConflictError(ValueError):
	"""Raised when a request key is reused with different assessment data."""


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


def _matches_idempotent_request(assessment: Assessment, data: AssessmentCreate) -> bool:
	if (
		assessment.assessment_status != data.assessment_status
		or assessment.assessment_data != data.assessment_data
	):
		return False
	return data.assessment_date is None or assessment.assessment_date == data.assessment_date


def create_assessment(
	db: Session,
	user: User,
	data: AssessmentCreate,
	idempotency_key: UUID | None = None,
) -> Assessment:
	values = data.model_dump(exclude_none=True)
	key = str(idempotency_key) if idempotency_key is not None else None
	if key is not None:
		existing = (
			db.query(Assessment)
			.filter(Assessment.user_id == user.id, Assessment.idempotency_key == key)
			.first()
		)
		if existing is not None:
			if _matches_idempotent_request(existing, data):
				return existing
			raise AssessmentIdempotencyConflictError(
				"Idempotency key was already used for a different assessment"
			)

	assessment = Assessment(user_id=user.id, idempotency_key=key, **values)
	db.add(assessment)
	try:
		db.commit()
	except IntegrityError:
		db.rollback()
		if key is None:
			raise
		existing = (
			db.query(Assessment)
			.filter(Assessment.user_id == user.id, Assessment.idempotency_key == key)
			.first()
		)
		if existing is None:
			raise
		if _matches_idempotent_request(existing, data):
			return existing
		raise AssessmentIdempotencyConflictError(
			"Idempotency key was already used for a different assessment"
		)
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
