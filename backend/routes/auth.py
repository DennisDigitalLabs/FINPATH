import smtplib

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.dependencies import get_current_user, get_db
from backend.models import User
from backend.config import get_settings
from backend.schemas.user import (
	PasswordResetConfirm,
	PasswordResetRequest,
	PasswordResetToken,
	TokenResponse,
	UserCreate,
	UserLogin,
	UserResponse,
)
from backend.services.auth_service import (
	authenticate_user,
	create_password_reset_token,
	get_user_by_email,
	get_user_from_password_reset_token,
	issue_access_token,
	normalize_email,
	register_user,
	reset_password,
)
from backend.services.email_service import password_reset_email_configured, send_password_reset_email
from backend.rate_limiter import auth_rate_limiter


router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
LOGIN_FAILURE_LIMIT = 5
PASSWORD_RESET_REQUEST_LIMIT = 3
AUTH_RATE_LIMIT_WINDOW_SECONDS = 900


def _rate_limited(retry_after: int) -> HTTPException:
	return HTTPException(
		status_code=status.HTTP_429_TOO_MANY_REQUESTS,
		detail="Too many attempts. Please try again later.",
		headers={"Retry-After": str(retry_after)},
	)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)) -> User:
	try:
		return register_user(db, user_data)
	except ValueError as exc:
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
	except IntegrityError:
		db.rollback()
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")


@router.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
	email = normalize_email(str(credentials.email))
	retry_after = auth_rate_limiter.retry_after(
		"login",
		email,
		LOGIN_FAILURE_LIMIT,
		AUTH_RATE_LIMIT_WINDOW_SECONDS,
	)
	if retry_after:
		raise _rate_limited(retry_after)
	user = authenticate_user(db, credentials)
	if user is None:
		auth_rate_limiter.record("login", email, AUTH_RATE_LIMIT_WINDOW_SECONDS)
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Invalid email or password",
			headers={"WWW-Authenticate": "Bearer"},
		)
	auth_rate_limiter.clear("login", email)
	return TokenResponse(access_token=issue_access_token(user))


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(
	request: PasswordResetRequest,
	db: Session = Depends(get_db),
) -> dict[str, str]:
	settings = get_settings()
	if not password_reset_email_configured():
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail="Password reset is temporarily unavailable.",
		)
	email = str(request.email)
	normalized_email = normalize_email(email)
	retry_after = auth_rate_limiter.retry_after(
		"password_reset",
		normalized_email,
		PASSWORD_RESET_REQUEST_LIMIT,
		AUTH_RATE_LIMIT_WINDOW_SECONDS,
	)
	if retry_after:
		return {"message": "If an account exists for that email, a password reset link will be sent shortly."}
	auth_rate_limiter.record(
		"password_reset",
		normalized_email,
		AUTH_RATE_LIMIT_WINDOW_SECONDS,
	)
	user = get_user_by_email(db, normalized_email)
	reset_url = None
	if user is not None and user.is_active:
		token = create_password_reset_token(user)
		reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password#token={token}"
	try:
		send_password_reset_email(str(request.email), reset_url)
	except (OSError, RuntimeError, smtplib.SMTPException) as exc:
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail="Password reset is temporarily unavailable.",
		) from exc
	return {"message": "If an account exists for that email, a password reset link will be sent shortly."}


@router.post("/reset-password/validate")
def validate_password_reset_token(
	request: PasswordResetToken,
	db: Session = Depends(get_db),
) -> dict[str, bool]:
	if get_user_from_password_reset_token(db, request.token) is None:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This reset link is invalid or has expired.")
	return {"valid": True}


@router.post("/reset-password")
def confirm_password_reset(
	request: PasswordResetConfirm,
	db: Session = Depends(get_db),
) -> dict[str, str]:
	user = get_user_from_password_reset_token(db, request.token)
	if user is None:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This reset link is invalid or has expired.")
	reset_password(db, user, request.password)
	return {"message": "Your password has been reset successfully."}


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
	return current_user
