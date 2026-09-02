from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.dependencies import get_current_user, get_db
from backend.models import Assessment, User
from backend.schemas.assessment import AssessmentCreate, AssessmentResponse, AssessmentUpdate
from backend.services.assessment_service import (
	create_assessment,
	delete_assessment,
	get_user_assessment,
	list_user_assessments,
	update_assessment,
)


router = APIRouter(prefix="/api/v1/assessments", tags=["assessments"])


@router.post("", response_model=AssessmentResponse, status_code=status.HTTP_201_CREATED)
def create(
	data: AssessmentCreate,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
) -> Assessment:
	return create_assessment(db, current_user, data)


@router.get("", response_model=list[AssessmentResponse])
def list_all(
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
) -> list[Assessment]:
	return list_user_assessments(db, current_user)


@router.get("/{assessment_id}", response_model=AssessmentResponse)
def get_one(
	assessment_id: int,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
) -> Assessment:
	assessment = get_user_assessment(db, assessment_id, current_user)
	if assessment is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
	return assessment


@router.put("/{assessment_id}", response_model=AssessmentResponse)
def update(
	assessment_id: int,
	data: AssessmentUpdate,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
) -> Assessment:
	assessment = get_user_assessment(db, assessment_id, current_user)
	if assessment is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
	return update_assessment(db, assessment, data)


@router.delete("/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
	assessment_id: int,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
) -> None:
	assessment = get_user_assessment(db, assessment_id, current_user)
	if assessment is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
	delete_assessment(db, assessment)
