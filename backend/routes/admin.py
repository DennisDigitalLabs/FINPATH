import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.dependencies import get_current_admin, get_db
from backend.models import OperationalEvent, User
from backend.schemas.admin import (
	AdminBootstrapCreate,
	AdminBootstrapStatus,
	AdminAuditLogListResponse,
	AdminOperationalEventListResponse,
	AdminOperationalEventResponse,
	AdminOperationalSummaryResponse,
	AdminManagedUserCreate,
	AdminHealthResponse,
	AdminModelMonitoringResponse,
	AdminRecordListResponse,
	AdminRecordType,
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
	add_admin_audit_log,
	create_admin_account,
	create_standard_user,
	acknowledge_operational_event,
	get_admin_operational_summary,
	get_admin_model_monitoring,
	list_admin_audit_logs,
	list_admin_users,
	list_admin_operational_events,
	list_admin_records,
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
		return create_standard_user(db, user_data, _admin)
	except ValueError as exc:
		add_admin_audit_log(
			db,
			_admin.id,
			"user.creation_rejected",
			"user",
			outcome="failure",
		)
		db.commit()
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail=str(exc),
		) from exc
	except IntegrityError as exc:
		db.rollback()
		add_admin_audit_log(
			db,
			_admin.id,
			"user.creation_rejected",
			"user",
			outcome="failure",
		)
		db.commit()
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
		return create_admin_account(db, admin_data, _admin)
	except ValueError as exc:
		add_admin_audit_log(
			db,
			_admin.id,
			"admin.account_creation_rejected",
			"user",
			outcome="failure",
		)
		db.commit()
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail=str(exc),
		) from exc


@router.get("/users", response_model=AdminUserListResponse)
def list_users(
	search: str | None = Query(default=None, max_length=100),
	page: int = Query(default=1, ge=1),
	page_size: int = Query(default=10, ge=1, le=100),
	is_active: bool | None = Query(default=None),
	db: Session = Depends(get_db),
	_admin: User = Depends(get_current_admin),
) -> AdminUserListResponse:
	items, total = list_admin_users(db, search, page, page_size, is_active)
	return AdminUserListResponse(
		items=items,
		total=total,
		page=page,
		page_size=page_size,
	)


@router.get("/records/{record_type}", response_model=AdminRecordListResponse)
def list_records(
	record_type: AdminRecordType,
	search: str | None = Query(default=None, max_length=100),
	filter_value: str | None = Query(default=None, max_length=100),
	page: int = Query(default=1, ge=1),
	page_size: int = Query(default=10, ge=1, le=100),
	db: Session = Depends(get_db),
	_admin: User = Depends(get_current_admin),
) -> AdminRecordListResponse:
	items, total = list_admin_records(
		db, record_type, search, filter_value, page, page_size
	)
	return AdminRecordListResponse(
		record_type=record_type,
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
		add_admin_audit_log(
			db, admin.id, "user.status_change_rejected", "user", str(user_id),
			outcome="failure",
		)
		db.commit()
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="User not found",
		)
	if user.id == admin.id or user.role != "user":
		add_admin_audit_log(
			db, admin.id, "user.status_change_rejected", "user", str(user.id),
			outcome="failure",
		)
		db.commit()
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail="Administrator accounts cannot be managed through this endpoint",
		)

	return update_user_active_status(db, user, update.is_active, admin)


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


@router.get("/model", response_model=AdminModelMonitoringResponse)
def admin_model_monitoring(
	db: Session = Depends(get_db),
	_admin: User = Depends(get_current_admin),
) -> AdminModelMonitoringResponse:
	from backend.routes.prediction import prediction_service

	return AdminModelMonitoringResponse(
		**get_admin_model_monitoring(
			db,
			prediction_service.model_available,
			prediction_service.model_version,
		),
		generated_at=datetime.now(timezone.utc),
	)


@router.get("/audit-logs", response_model=AdminAuditLogListResponse)
def list_audit_logs(
	action: str | None = Query(default=None, max_length=100),
	actor_user_id: int | None = Query(default=None, ge=1),
	outcome: str | None = Query(default=None, pattern="^(success|failure|unknown)$"),
	created_after: datetime | None = Query(default=None),
	created_before: datetime | None = Query(default=None),
	page: int = Query(default=1, ge=1),
	page_size: int = Query(default=10, ge=1, le=100),
	db: Session = Depends(get_db),
	_admin: User = Depends(get_current_admin),
) -> AdminAuditLogListResponse:
	if created_after is not None and created_before is not None and created_after > created_before:
		raise HTTPException(
			status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
			detail="created_after must not be later than created_before",
		)
	items, total = list_admin_audit_logs(
		db,
		page,
		page_size,
		action,
		actor_user_id,
		outcome,
		created_after,
		created_before,
	)
	return AdminAuditLogListResponse(
		items=items, total=total, page=page, page_size=page_size
	)


@router.get("/operational-events", response_model=AdminOperationalEventListResponse)
def list_operational_events(
	page: int = Query(default=1, ge=1),
	page_size: int = Query(default=10, ge=1, le=100),
	status_filter: str | None = Query(default=None, pattern="^(open|acknowledged)$"),
	severity_filter: str | None = Query(
		default=None, pattern="^(info|warning|error|critical)$"
	),
	db: Session = Depends(get_db),
	_admin: User = Depends(get_current_admin),
) -> AdminOperationalEventListResponse:
	items, total = list_admin_operational_events(
		db,
		page,
		page_size,
		status_filter=status_filter,
		severity_filter=severity_filter,
	)
	return AdminOperationalEventListResponse(
		items=items, total=total, page=page, page_size=page_size
	)


@router.get("/alerts", response_model=AdminOperationalEventListResponse)
def list_operational_alerts(
	page: int = Query(default=1, ge=1),
	page_size: int = Query(default=10, ge=1, le=100),
	db: Session = Depends(get_db),
	_admin: User = Depends(get_current_admin),
) -> AdminOperationalEventListResponse:
	items, total = list_admin_operational_events(
		db, page, page_size, alerts_only=True
	)
	return AdminOperationalEventListResponse(
		items=items, total=total, page=page, page_size=page_size
	)


@router.post(
	"/alerts/{event_id}/acknowledge",
	response_model=AdminOperationalEventResponse,
)
def acknowledge_alert(
	event_id: int,
	db: Session = Depends(get_db),
	admin: User = Depends(get_current_admin),
) -> OperationalEvent:
	event = db.get(OperationalEvent, event_id)
	if event is None:
		add_admin_audit_log(
			db,
			admin.id,
			"operational_event.acknowledgement_rejected",
			"operational_event",
			str(event_id),
			outcome="failure",
		)
		db.commit()
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
	if event.status != "open" or event.severity not in {"warning", "error", "critical"}:
		add_admin_audit_log(
			db,
			admin.id,
			"operational_event.acknowledgement_rejected",
			"operational_event",
			str(event.id),
			outcome="failure",
		)
		db.commit()
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail="Alert is not open for acknowledgement",
		)
	acknowledged = acknowledge_operational_event(db, event, admin)
	if acknowledged is None:
		add_admin_audit_log(
			db,
			admin.id,
			"operational_event.acknowledgement_rejected",
			"operational_event",
			str(event.id),
			outcome="failure",
		)
		db.commit()
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail="Alert is not open for acknowledgement",
		)
	return acknowledged


@router.get("/operational-summary", response_model=AdminOperationalSummaryResponse)
def operational_summary(
	db: Session = Depends(get_db),
	_admin: User = Depends(get_current_admin),
) -> AdminOperationalSummaryResponse:
	return AdminOperationalSummaryResponse(
		**get_admin_operational_summary(db),
		generated_at=datetime.now(timezone.utc),
	)
