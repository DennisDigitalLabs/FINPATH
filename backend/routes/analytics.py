from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.dependencies import get_current_admin, get_current_user, get_db
from backend.models import User
from backend.schemas.dashboard import AnalyticsResponse, SystemAnalyticsResponse
from backend.services.analytics_service import get_system_analytics, get_user_analytics


router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("", response_model=AnalyticsResponse)
def user_analytics(
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
) -> AnalyticsResponse:
	return get_user_analytics(db, current_user)


@router.get("/system", response_model=SystemAnalyticsResponse)
def system_analytics(
	db: Session = Depends(get_db),
	_admin: User = Depends(get_current_admin),
) -> SystemAnalyticsResponse:
	return get_system_analytics(db)
