from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.dependencies import get_current_user, get_db
from backend.models import Recommendation, User
from backend.schemas.recommendation import RecommendationResponse
from backend.services.recommendation_service import (
	get_user_recommendation,
	list_user_recommendations,
)


router = APIRouter(prefix="/api/v1/recommendations", tags=["recommendations"])


@router.get("", response_model=list[RecommendationResponse])
def list_recommendations(
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
) -> list[Recommendation]:
	return list_user_recommendations(db, current_user)


@router.get("/{recommendation_id}", response_model=RecommendationResponse)
def get_recommendation(
	recommendation_id: int,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
) -> Recommendation:
	recommendation = get_user_recommendation(db, recommendation_id, current_user)
	if recommendation is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Recommendation not found",
		)
	return recommendation
