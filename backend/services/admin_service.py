from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from backend.models import User
from backend.schemas.user import UserCreate
from backend.services.auth_service import register_user


def create_standard_user(db: Session, user_data: UserCreate) -> User:
	return register_user(db, user_data)


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
