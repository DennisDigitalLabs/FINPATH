import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from sqlalchemy.orm import Session

from backend.config import get_settings
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


def _password_fingerprint(password_hash: str) -> str:
	return hashlib.sha256(password_hash.encode("utf-8")).hexdigest()


def create_password_reset_token(user: User) -> str:
	settings = get_settings()
	now = datetime.now(timezone.utc)
	payload = {
		"sub": str(user.id),
		"type": "password_reset",
		"iat": now,
		"exp": now + timedelta(minutes=settings.RESET_TOKEN_EXPIRE_MINUTES),
		"jti": secrets.token_urlsafe(32),
		"ph": _password_fingerprint(user.hashed_password),
	}
	return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_user_from_password_reset_token(db: Session, token: str) -> User | None:
	settings = get_settings()
	try:
		payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
	except JWTError:
		return None
	if payload.get("type") != "password_reset" or not payload.get("jti"):
		return None
	user_id = payload.get("sub")
	if not user_id or payload.get("ph") is None:
		return None
	try:
		user = db.get(User, int(user_id))
	except (TypeError, ValueError):
		return None
	if user is None or not user.is_active:
		return None
	if payload["ph"] != _password_fingerprint(user.hashed_password):
		return None
	return user


def reset_password(db: Session, user: User, password: str) -> None:
	user.hashed_password = hash_password(password)
	db.commit()
