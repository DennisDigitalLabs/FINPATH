"""
FINPATH Backend Dependencies

FastAPI dependency injection functions for database sessions, authentication, and other shared resources.
"""

from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import SessionLocal
from backend.models import User
from backend.security import decode_access_token


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency to inject database session into route handlers.
    
    Automatically manages session lifecycle (creation and cleanup).
    
    Example:
        @router.get("/items/")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    
    Yields:
        SQLAlchemy Session object
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        subject = payload.get("sub")
        user_id = int(subject) if subject is not None else None
    except (JWTError, TypeError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    owner_email = get_settings().ADMIN_OWNER_EMAIL
    if not owner_email:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Administrator access is not configured",
        )
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )
    return current_user
