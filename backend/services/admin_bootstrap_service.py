from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models import User
from backend.schemas.user import AdminCreate
from backend.security import hash_password
from backend.services.auth_service import (
	count_admin_users,
	create_admin_user,
	normalize_email,
)


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
		db.commit()
	except SQLAlchemyError:
		db.rollback()
		raise
	db.refresh(existing_owner)
	return existing_owner
