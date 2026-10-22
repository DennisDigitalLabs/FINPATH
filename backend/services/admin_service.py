from sqlalchemy import func, or_
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from backend.models import User
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


def create_standard_user(db: Session, user_data: UserCreate) -> User:
	return register_user(db, user_data)


def create_admin_account(db: Session, admin_data: AdminCreate) -> User:
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
) -> tuple[list[User], int]:
	query = db.query(User)
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


def update_user_active_status(
	db: Session,
	user: User,
	is_active: bool,
) -> User:
	user.is_active = is_active
	db.commit()
	db.refresh(user)
	return user
