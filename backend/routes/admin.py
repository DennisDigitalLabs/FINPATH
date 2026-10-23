import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.dependencies import get_current_admin, get_db
from backend.models import User
from backend.schemas.admin import (
	AdminBootstrapCreate,
	AdminBootstrapStatus,
	AdminManagedUserCreate,
	AdminHealthResponse,
	AdminUserListResponse,
	AdminUserResponse,
	AdminUserStatusUpdate,
)
from backend.schemas.user import AdminCreate
from backend.services.admin_bootstrap_service import (
	AdminBootstrapAuthorizationError,
	AdminBootstrapUnavailableError,
	bootstrap_first_admin,
	get_first_admin_setup_status,
)
from backend.services.admin_service import (
	create_admin_account,
	create_standard_user,
	list_admin_users,
	update_user_active_status,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/admin", tags=["administration"])


@router.get("/bootstrap/status", response_model=AdminBootstrapStatus)
def admin_bootstrap_status(
	db: Session = Depends(get_db),
) -> AdminBootstrapStatus:
	return AdminBootstrapStatus(**get_first_admin_setup_status(db))


@router.post(
	"/bootstrap",
	response_model=AdminUserResponse,
	status_code=status.HTTP_201_CREATED,
)
def create_first_admin(
	admin_data: AdminBootstrapCreate,
	db: Session = Depends(get_db),
) -> User:
	try:
		return bootstrap_first_admin(
			db,
			admin_data,
			admin_data.bootstrap_token,
			admin_data.confirm_existing_owner,
		)
	except AdminBootstrapAuthorizationError as exc:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail="Bootstrap authorization failed.",
		) from exc
	except AdminBootstrapUnavailableError as exc:
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail=str(exc),
		) from exc
	except ValueError as exc:
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail=str(exc),
		) from exc
	except IntegrityError as exc:
		db.rollback()
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail="First administrator setup has already been completed.",
		) from exc
	except DBAPIError as exc:
		db.rollback()
		if "database is locked" in str(exc.orig).lower():
			raise HTTPException(
				status_code=status.HTTP_409_CONFLICT,
				detail="First administrator setup is in progress. Please retry shortly.",
			) from exc
		raise


@router.post(
	"/users",
	response_model=AdminUserResponse,
	status_code=status.HTTP_201_CREATED,
)
def create_user(
	user_data: AdminManagedUserCreate,
	db: Session = Depends(get_db),
	_admin: User = Depends(get_current_admin),
) -> User:
	try:
		return create_standard_user(db, user_data)
	except ValueError as exc:
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail=str(exc),
		) from exc
	except IntegrityError as exc:
		db.rollback()
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail="An account with this email already exists",
		) from exc


@router.post(
	"/admins",
	response_model=AdminUserResponse,
	status_code=status.HTTP_201_CREATED,
)
def create_admin(
	admin_data: AdminCreate,
	db: Session = Depends(get_db),
	_admin: User = Depends(get_current_admin),
) -> User:
	try:
		return create_admin_account(db, admin_data)
	except ValueError as exc:
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail=str(exc),
		) from exc


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
