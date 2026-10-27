from datetime import datetime, timezone

from sqlalchemy import func, or_, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
	AdminAuditLog,
	Assessment,
	OperationalEvent,
	Prediction,
	Recommendation,
	User,
)
from backend.schemas.admin import AdminRecordType
from backend.schemas.user import AdminCreate, UserCreate
from backend.security import hash_password
from backend.services.auth_service import (
	count_admin_users,
	get_user_by_email,
	register_user,
)


ADMIN_LIMIT_MESSAGE = (
	"The maximum of 2 active administrator accounts has been reached. "
	"Please contact the system administrator."
)


def create_standard_user(db: Session, user_data: UserCreate, actor: User) -> User:
	return register_user(db, user_data, admin_actor_id=actor.id)


def create_admin_account(
	db: Session, admin_data: AdminCreate, actor: User | None = None
) -> User:
	email = str(admin_data.email).strip().lower()
	if get_user_by_email(db, email) is not None:
		raise ValueError("An account with this email already exists")
	if count_admin_users(db) >= 2:
		raise ValueError(ADMIN_LIMIT_MESSAGE)

	user = User(
		full_name=admin_data.full_name,
		email=email,
		hashed_password=hash_password(admin_data.password),
		role="admin",
		is_active=True,
	)
	db.add(user)
	try:
		db.flush()
		db.add(AdminAuditLog(
			actor_user_id=actor.id if actor else None,
			action="admin.account_created",
			target_type="user",
			target_id=str(user.id),
			outcome="success",
		))
		db.commit()
	except DBAPIError as exc:
		db.rollback()
		message = str(exc.orig).lower()
		if "maximum of two active admin accounts exceeded" in message:
			raise ValueError(ADMIN_LIMIT_MESSAGE) from exc
		if isinstance(exc, IntegrityError):
			raise ValueError("An account with this email already exists") from exc
		raise
	db.refresh(user)
	return user


def list_admin_users(
	db: Session,
	search: str | None,
	page: int,
	page_size: int,
	is_active: bool | None = None,
) -> tuple[list[User], int]:
	query = db.query(User)
	if is_active is not None:
		query = query.filter(User.is_active.is_(is_active))
	search_term = (search or "").strip()
	if search_term:
		escaped_search = (
			search_term.replace("\\", "\\\\")
			.replace("%", "\\%")
			.replace("_", "\\_")
		)
		pattern = f"%{escaped_search}%"
		query = query.filter(or_(
			User.full_name.ilike(pattern, escape="\\"),
			User.email.ilike(pattern, escape="\\"),
		))

	total = query.with_entities(func.count(User.id)).scalar() or 0
	items = (
		query.order_by(User.created_at.desc(), User.id.desc())
		.offset((page - 1) * page_size)
		.limit(page_size)
		.all()
	)
	return items, total


def list_admin_records(
	db: Session,
	record_type: AdminRecordType,
	search: str | None,
	filter_value: str | None,
	page: int,
	page_size: int,
) -> tuple[list[dict], int]:
	search_term = (search or "").strip()
	filter_term = (filter_value or "").strip()
	if record_type == "assessments":
		query = db.query(
			Assessment.id.label("id"),
			Assessment.user_id.label("user_id"),
			User.full_name.label("full_name"),
			User.email.label("email"),
			Assessment.created_at.label("created_at"),
			Assessment.assessment_status.label("status"),
		).join(User, Assessment.user_id == User.id)
		count_query = db.query(func.count(Assessment.id)).join(
			User, Assessment.user_id == User.id
		)
		filter_column = Assessment.assessment_status
		search_columns = (User.full_name, User.email, Assessment.assessment_status)
	elif record_type == "predictions":
		query = db.query(
			Prediction.id.label("id"),
			Assessment.user_id.label("user_id"),
			User.full_name.label("full_name"),
			User.email.label("email"),
			Prediction.created_at.label("created_at"),
			Prediction.assessment_id.label("assessment_id"),
			Prediction.risk_level.label("risk_level"),
			Prediction.risk_category.label("risk_category"),
			Prediction.probability.label("probability"),
			Prediction.model_version.label("model_version"),
		).join(Assessment, Prediction.assessment_id == Assessment.id).join(
			User, Assessment.user_id == User.id
		)
		count_query = db.query(func.count(Prediction.id)).join(
			Assessment, Prediction.assessment_id == Assessment.id
		).join(User, Assessment.user_id == User.id)
		filter_column = Prediction.risk_level
		search_columns = (
			User.full_name, User.email, Prediction.risk_level,
			Prediction.risk_category, Prediction.model_version,
		)
	else:
		query = db.query(
			Recommendation.id.label("id"),
			Assessment.user_id.label("user_id"),
			User.full_name.label("full_name"),
			User.email.label("email"),
			Recommendation.created_at.label("created_at"),
			Prediction.id.label("prediction_id"),
			Recommendation.category.label("category"),
			Recommendation.priority.label("priority"),
			Recommendation.recommendation_text.label("recommendation_text"),
		).join(Prediction, Recommendation.prediction_id == Prediction.id).join(
			Assessment, Prediction.assessment_id == Assessment.id
		).join(User, Assessment.user_id == User.id)
		count_query = db.query(func.count(Recommendation.id)).join(
			Prediction, Recommendation.prediction_id == Prediction.id
		).join(Assessment, Prediction.assessment_id == Assessment.id).join(
			User, Assessment.user_id == User.id
		)
		filter_column = Recommendation.category
		search_columns = (
			User.full_name, User.email, Recommendation.category,
			Recommendation.recommendation_text,
		)

	if search_term:
		escaped_search = (
			search_term.replace("\\", "\\\\")
			.replace("%", "\\%")
			.replace("_", "\\_")
		)
		pattern = f"%{escaped_search}%"
		conditions = [column.ilike(pattern, escape="\\") for column in search_columns]
		if search_term.isdecimal() and len(search_term) <= 18:
			conditions.append(
				(Assessment.id if record_type == "assessments" else
				 Prediction.id if record_type == "predictions" else
				 Recommendation.id) == int(search_term)
			)
		query = query.filter(or_(*conditions))
		count_query = count_query.filter(or_(*conditions))
	if filter_term:
		query = query.filter(func.lower(filter_column) == filter_term.lower())
		count_query = count_query.filter(func.lower(filter_column) == filter_term.lower())

	total = count_query.scalar() or 0
	rows = (
		query.order_by(
			Assessment.created_at.desc() if record_type == "assessments" else
			Prediction.created_at.desc() if record_type == "predictions" else
			Recommendation.created_at.desc(),
			Assessment.id.desc() if record_type == "assessments" else
			Prediction.id.desc() if record_type == "predictions" else
			Recommendation.id.desc(),
		)
		.offset((page - 1) * page_size)
		.limit(page_size)
		.all()
	)
	return [dict(row._mapping) for row in rows], total


def get_admin_model_monitoring(
	db: Session,
	model_available: bool,
	model_version: str | None,
) -> dict:
	return {
		"model_available": model_available,
		"model_version": model_version,
		"recorded_prediction_count": db.query(func.count(Prediction.id)).scalar() or 0,
		"recorded_model_versions": {
			version: count
			for version, count in db.query(
				Prediction.model_version, func.count(Prediction.id)
			).group_by(Prediction.model_version).all()
		},
		"explanation_available_count": db.query(func.count(Prediction.id)).filter(
			Prediction.explanation.is_not(None),
			func.trim(Prediction.explanation) != "",
		).scalar() or 0,
		"contributing_factors_available_count": db.query(
			func.count(Prediction.id)
		).filter(Prediction.contributing_factors.is_not(None)).scalar() or 0,
	}


def add_admin_audit_log(
	db: Session,
	actor_user_id: int | None,
	action: str,
	target_type: str | None = None,
	target_id: str | None = None,
	outcome: str = "unknown",
) -> AdminAuditLog:
	entry = AdminAuditLog(
		actor_user_id=actor_user_id,
		action=action,
		target_type=target_type,
		target_id=target_id,
		outcome=outcome,
	)
	db.add(entry)
	return entry


def record_operational_event(
	db: Session,
	event_type: str,
	source: str,
	severity: str,
	summary: str,
) -> OperationalEvent:
	event = OperationalEvent(
		event_type=event_type,
		source=source,
		severity=severity,
		summary=summary,
	)
	db.add(event)
	db.commit()
	db.refresh(event)
	return event


def list_admin_audit_logs(
	db: Session,
	page: int,
	page_size: int,
	action: str | None = None,
	actor_user_id: int | None = None,
	outcome: str | None = None,
	created_after: datetime | None = None,
	created_before: datetime | None = None,
) -> tuple[list[AdminAuditLog], int]:
	query = db.query(AdminAuditLog)
	if action:
		query = query.filter(AdminAuditLog.action == action)
	if actor_user_id is not None:
		query = query.filter(AdminAuditLog.actor_user_id == actor_user_id)
	if outcome:
		query = query.filter(AdminAuditLog.outcome == outcome)
	if created_after is not None:
		query = query.filter(AdminAuditLog.created_at >= created_after)
	if created_before is not None:
		query = query.filter(AdminAuditLog.created_at <= created_before)
	total = query.with_entities(func.count(AdminAuditLog.id)).scalar() or 0
	items = (
		query.order_by(AdminAuditLog.created_at.desc(), AdminAuditLog.id.desc())
		.offset((page - 1) * page_size)
		.limit(page_size)
		.all()
	)
	return items, total


def list_admin_operational_events(
	db: Session,
	page: int,
	page_size: int,
	status_filter: str | None = None,
	severity_filter: str | None = None,
	alerts_only: bool = False,
) -> tuple[list[OperationalEvent], int]:
	query = db.query(OperationalEvent)
	if status_filter is not None:
		query = query.filter(OperationalEvent.status == status_filter)
	if severity_filter is not None:
		query = query.filter(OperationalEvent.severity == severity_filter)
	if alerts_only:
		query = query.filter(
			OperationalEvent.status == "open",
			OperationalEvent.severity.in_(("warning", "error", "critical")),
		)
	total = query.with_entities(func.count(OperationalEvent.id)).scalar() or 0
	items = (
		query.order_by(
			OperationalEvent.occurred_at.desc(), OperationalEvent.id.desc()
		)
		.offset((page - 1) * page_size)
		.limit(page_size)
		.all()
	)
	return items, total


def get_admin_operational_summary(db: Session) -> dict[str, int]:
	return {
		"recorded_error_count": db.query(func.count(OperationalEvent.id)).filter(
			OperationalEvent.severity.in_(("error", "critical"))
		).scalar() or 0,
		"open_alert_count": db.query(func.count(OperationalEvent.id)).filter(
			OperationalEvent.status == "open",
			OperationalEvent.severity.in_(("warning", "error", "critical")),
		).scalar() or 0,
	}


def acknowledge_operational_event(
	db: Session, event: OperationalEvent, actor: User
) -> OperationalEvent | None:
	acknowledged_at = datetime.now(timezone.utc)
	result = db.execute(
		update(OperationalEvent)
		.where(
			OperationalEvent.id == event.id,
			OperationalEvent.status == "open",
			OperationalEvent.severity.in_(("warning", "error", "critical")),
		)
		.values(
			status="acknowledged",
			acknowledged_at=acknowledged_at,
			acknowledged_by_user_id=actor.id,
		)
	)
	if result.rowcount != 1:
		db.rollback()
		return None
	add_admin_audit_log(
		db,
		actor.id,
		"operational_event.acknowledged",
		"operational_event",
		str(event.id),
		outcome="success",
	)
	db.commit()
	db.expire(event)
	db.refresh(event)
	return event


def update_user_active_status(
	db: Session,
	user: User,
	is_active: bool,
	actor: User,
) -> User:
	user.is_active = is_active
	add_admin_audit_log(
		db,
		actor.id,
		"user.activated" if is_active else "user.deactivated",
		"user",
		str(user.id),
		outcome="success",
	)
	db.commit()
	db.refresh(user)
	return user
