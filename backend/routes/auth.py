import smtplib

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.dependencies import get_current_admin, get_current_user, get_db
from backend.models import User
from backend.config import get_settings
from backend.schemas.user import (
	AdminCreate,
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
	create_admin_user,
	create_password_reset_token,
	get_user_by_email,
	get_user_from_password_reset_token,
	issue_access_token,
	register_user,
	reset_password,
)
from backend.services.email_service import password_reset_email_configured, send_password_reset_email


router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)) -> User:
	try:
		return register_user(db, user_data)
	except ValueError as exc:
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
	except IntegrityError:
		db.rollback()
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")


@router.post("/admins", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_admin_account(
	admin_data: AdminCreate,
	db: Session = Depends(get_db),
	_admin: User = Depends(get_current_admin),
) -> User:
	try:
		return create_admin_user(db, admin_data)
	except ValueError as exc:
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
	user = authenticate_user(db, credentials)
	if user is None:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Invalid email or password",
			headers={"WWW-Authenticate": "Bearer"},
		)
	return TokenResponse(access_token=issue_access_token(user))


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(
	request: PasswordResetRequest,
	db: Session = Depends(get_db),
) -> dict[str, str]:
	settings = get_settings()
	user = get_user_by_email(db, str(request.email))
	if not password_reset_email_configured():
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail="Password reset is temporarily unavailable.",
		)
	if user is not None and user.is_active:
		token = create_password_reset_token(user)
		reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password.html#token={token}"
		try:
			send_password_reset_email(str(user.email), reset_url)
		except (OSError, RuntimeError, smtplib.SMTPException):
			raise HTTPException(
				status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
				detail="Password reset is temporarily unavailable.",
			)
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
