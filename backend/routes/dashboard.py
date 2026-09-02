from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.dependencies import get_current_user, get_db
from backend.models import User
from backend.schemas.dashboard import DashboardResponse
from backend.services.dashboard_service import get_user_dashboard


router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
def dashboard(
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
) -> DashboardResponse:
	return get_user_dashboard(db, current_user)
