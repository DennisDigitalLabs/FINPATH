import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.dependencies import get_current_user, get_db
from backend.models import Prediction, User
from backend.schemas.prediction import PredictionRequest, PredictionResponse
from backend.services.admin_service import record_operational_event
from backend.services.prediction_service import (
	PredictionService,
	PredictionUnavailableError,
	RealFinpathPredictor,
	get_user_assessment_predictions,
	get_user_prediction,
)
from backend.services.assessment_service import get_user_assessment


router = APIRouter(prefix="/api/v1", tags=["predictions"])
logger = logging.getLogger(__name__)
try:
	prediction_service = PredictionService(RealFinpathPredictor())
except PredictionUnavailableError:
	prediction_service = PredictionService()


@router.post(
	"/predictions",
	response_model=PredictionResponse,
	status_code=status.HTTP_201_CREATED,
	responses={
		404: {"description": "Assessment not found or not accessible"},
		409: {"description": "Assessment is not ready or prediction output is invalid"},
		503: {"description": "Prediction service is unavailable"},
	},
)
def create_prediction(
	request: PredictionRequest,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
) -> Prediction:
	assessment = get_user_assessment(db, request.assessment_id, current_user)
	if assessment is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
	try:
		return prediction_service.generate_and_store(db, assessment, current_user)
	except PredictionUnavailableError:
		try:
			record_operational_event(
				db,
				"prediction.unavailable",
				"prediction",
				"error",
				"The prediction service could not process a request.",
			)
		except SQLAlchemyError:
			db.rollback()
			logger.error("Could not persist a prediction service failure event")
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail="Prediction service is currently unavailable",
		)
	except ValueError as exc:
		try:
			record_operational_event(
				db,
				"prediction.generation_failed",
				"prediction",
				"error",
				"Prediction generation failed validation.",
			)
		except SQLAlchemyError:
			db.rollback()
			logger.error("Could not persist a prediction validation failure event")
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/predictions/{prediction_id}", response_model=PredictionResponse)
def get_prediction(
	prediction_id: int,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
) -> Prediction:
	prediction = get_user_prediction(db, prediction_id, current_user)
	if prediction is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found")
	return prediction


@router.get(
	"/assessments/{assessment_id}/predictions",
	response_model=list[PredictionResponse],
)
def list_predictions(
	assessment_id: int,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
) -> list[Prediction]:
	assessment = get_user_assessment(db, assessment_id, current_user)
	if assessment is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
	return get_user_assessment_predictions(db, assessment_id, current_user)
