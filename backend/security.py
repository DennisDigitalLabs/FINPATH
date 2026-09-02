from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.config import get_settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
	return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
	try:
		return pwd_context.verify(plain_password, password_hash)
	except (TypeError, ValueError):
		return False


def create_access_token(subject: str, role: str) -> str:
	settings = get_settings()
	now = datetime.now(timezone.utc)
	payload: dict[str, Any] = {
		"sub": subject,
		"role": role,
		"iat": now,
		"exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
	}
	return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
	settings = get_settings()
	return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
