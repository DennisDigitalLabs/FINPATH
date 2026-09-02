from sqlalchemy.orm import Session

from backend.models import User
from backend.schemas.user import UserCreate, UserLogin
from backend.security import create_access_token, hash_password, verify_password


def normalize_email(email: str) -> str:
	return email.strip().lower()


def get_user_by_email(db: Session, email: str) -> User | None:
	return db.query(User).filter(User.email == normalize_email(email)).first()


def register_user(db: Session, user_data: UserCreate) -> User:
	email = normalize_email(str(user_data.email))
	if get_user_by_email(db, email) is not None:
		raise ValueError("An account with this email already exists")

	user = User(
		full_name=user_data.full_name,
		email=email,
		hashed_password=hash_password(user_data.password),
		role="user",
	)
	db.add(user)
	db.commit()
	db.refresh(user)
	return user


def authenticate_user(db: Session, credentials: UserLogin) -> User | None:
	user = get_user_by_email(db, str(credentials.email))
	if user is None or not verify_password(credentials.password, user.hashed_password):
		return None
	if not user.is_active:
		return None
	return user


def issue_access_token(user: User) -> str:
	return create_access_token(subject=str(user.id), role=user.role)
