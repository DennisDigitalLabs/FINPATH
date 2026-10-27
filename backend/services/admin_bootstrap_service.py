import hmac

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import func, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models import AdminAuditLog, User
from backend.schemas.user import AdminCreate
from backend.security import hash_password
from backend.services.auth_service import (
	count_admin_users,
	create_admin_user,
	normalize_email,
)


class AdminBootstrapUnavailableError(RuntimeError):
	"""Raised when public first-owner setup is not configured or is closed."""


class AdminBootstrapAuthorizationError(PermissionError):
	"""Raised when a submitted first-owner bootstrap token is incorrect."""


def _validated_configured_owner_email(value: str) -> str | None:
	try:
		return normalize_email(str(TypeAdapter(EmailStr).validate_python(value)))
	except ValidationError:
		return None


def _lock_first_admin_bootstrap(db: Session) -> None:
	dialect = db.get_bind().dialect.name
	if dialect == "postgresql":
		db.execute(text("SELECT pg_advisory_xact_lock(7346159021)"))


def get_configured_owner(db: Session, owner_email: str) -> User | None:
	matches = (
		db.query(User)
		.filter(func.lower(User.email) == normalize_email(owner_email))
		.limit(2)
		.all()
	)
	if len(matches) > 1:
		raise ValueError(
			"Multiple accounts match ADMIN_OWNER_EMAIL; operator review is required."
		)
	return matches[0] if matches else None


def get_first_admin_setup_status(db: Session) -> dict[str, bool]:
	settings = get_settings()
	owner_email = _validated_configured_owner_email(settings.ADMIN_OWNER_EMAIL)
	configured = bool(owner_email and len(settings.ADMIN_BOOTSTRAP_TOKEN) >= 32)
	administrator_exists = count_admin_users(db) > 0
	return {
		"setup_available": configured and not administrator_exists,
		"administrator_exists": administrator_exists,
		"setup_configured": configured,
	}


def bootstrap_first_admin(
	db: Session,
	owner_data: AdminCreate,
	bootstrap_token: str,
	confirm_existing_owner: bool = False,
) -> User:
	settings = get_settings()
	owner_email = _validated_configured_owner_email(settings.ADMIN_OWNER_EMAIL)
	if owner_email is None or len(settings.ADMIN_BOOTSTRAP_TOKEN) < 32:
		raise AdminBootstrapUnavailableError(
			"First administrator setup is not configured."
		)
	if not hmac.compare_digest(
		bootstrap_token.encode("utf-8"),
		settings.ADMIN_BOOTSTRAP_TOKEN.encode("utf-8"),
	):
		raise AdminBootstrapAuthorizationError("Bootstrap authorization failed.")
	_lock_first_admin_bootstrap(db)
	if count_admin_users(db) > 0:
		raise AdminBootstrapUnavailableError(
			"First administrator setup has already been completed."
		)
	if normalize_email(str(owner_data.email)) != owner_email:
		raise ValueError("Only the configured admin owner can be provisioned.")
	existing_owner = get_configured_owner(db, owner_email)
	if existing_owner is not None and not confirm_existing_owner:
		raise AdminBootstrapUnavailableError(
			"An account already exists for the configured owner email. Confirm that you "
			"want to reset its password and establish it as the first administrator."
		)
	return provision_configured_owner(
		db,
		owner_data,
		repair_existing=existing_owner is not None and confirm_existing_owner,
	)


def provision_configured_owner(
	db: Session,
	owner_data: AdminCreate,
	repair_existing: bool = False,
) -> User:
	owner_email = normalize_email(str(owner_data.email))
	if owner_email != normalize_email(get_settings().ADMIN_OWNER_EMAIL):
		raise ValueError("Only the configured admin owner can be provisioned.")
	existing_owner = get_configured_owner(db, owner_email)
	if existing_owner is None:
		return create_admin_user(db, owner_data)

	if existing_owner.is_active and existing_owner.role == "admin":
		raise ValueError("The configured administrator is already established.")
	if not repair_existing:
		raise ValueError(
			"The configured owner account exists but is inactive or has an "
			"inconsistent role. Explicit repair confirmation is required."
		)
	if count_admin_users(db) > 0:
		raise ValueError(
			"Other active administrator accounts exist. Review them through "
			"the trusted operator process before repairing the configured owner."
		)

	existing_owner.full_name = owner_data.full_name
	existing_owner.email = owner_email
	existing_owner.hashed_password = hash_password(owner_data.password)
	existing_owner.role = "admin"
	existing_owner.is_active = True
	try:
		db.add(AdminAuditLog(
			actor_user_id=None,
			action="admin.bootstrap_completed",
			target_type="user",
			target_id=str(existing_owner.id),
		))
		db.commit()
	except SQLAlchemyError:
		db.rollback()
		raise
	db.refresh(existing_owner)
	return existing_owner
