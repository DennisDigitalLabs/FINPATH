import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.dependencies import get_current_admin, get_db
from backend.models import User
from backend.schemas.admin import (
	AdminHealthResponse,
	AdminUserListResponse,
	AdminUserResponse,
	AdminUserStatusUpdate,
)
from backend.services.admin_service import (
	list_admin_users,
	update_user_active_status,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/admin", tags=["administration"])


@router.get("/users", response_model=AdminUserListResponse)
def list_users(
	search: str | None = Query(default=None, max_length=100),
	page: int = Query(default=1, ge=1),
	page_size: int = Query(default=10, ge=1, le=100),
	db: Session = Depends(get_db),
	_admin: User = Depends(get_current_admin),
) -> AdminUserListResponse:
	items, total = list_admin_users(db, search, page, page_size)
	return AdminUserListResponse(
		items=items,
		total=total,
		page=page,
		page_size=page_size,
	)


@router.patch("/users/{user_id}/status", response_model=AdminUserResponse)
def update_user_status(
	user_id: int,
	update: AdminUserStatusUpdate,
	db: Session = Depends(get_db),
	admin: User = Depends(get_current_admin),
) -> User:
	user = db.get(User, user_id)
	if user is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="User not found",
		)
	if user.id == admin.id or user.role != "user":
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail="Administrator accounts cannot be managed through this endpoint",
		)

	return update_user_active_status(db, user, update.is_active)


@router.get("/health", response_model=AdminHealthResponse)
def admin_health(
	db: Session = Depends(get_db),
	_admin: User = Depends(get_current_admin),
) -> AdminHealthResponse:
	try:
		db.execute(text("SELECT 1"))
	except SQLAlchemyError as exc:
		db.rollback()
		logger.warning("Admin health check database query failed", exc_info=exc)
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail="Database health check failed",
		) from exc
	return AdminHealthResponse(
		status="healthy",
		database="available",
		checked_at=datetime.now(timezone.utc),
	)
