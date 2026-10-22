"""Run with ``python -m backend.create_admin`` after database migrations."""

import sys
from getpass import getpass

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from backend.config import get_settings
from backend.database import SessionLocal
from backend.models import User
from backend.schemas.user import AdminCreate
from backend.services.auth_service import create_admin_user, get_user_by_email, normalize_email


def main() -> int:
	email = input("Admin email: ").strip()
	owner_email = normalize_email(get_settings().ADMIN_OWNER_EMAIL)
	if not owner_email:
		print("ADMIN_OWNER_EMAIL must be configured before provisioning the admin account.", file=sys.stderr)
		return 1
	if normalize_email(email) != owner_email:
		print("The supplied email does not match the configured admin owner.", file=sys.stderr)
		return 1

	try:
		with SessionLocal() as db:
			existing_user = get_user_by_email(db, owner_email)
			if existing_user is not None:
				if not existing_user.is_active:
					raise ValueError("The configured admin owner account is inactive.")
				other_admins = (
					db.query(User)
					.filter(
						User.role == "admin",
						User.is_active.is_(True),
						User.id != existing_user.id,
					)
					.all()
				)
				if other_admins:
					confirmation = input(
						f"Revoke admin access from {len(other_admins)} other active account(s)? Type REVOKE to confirm: "
					).strip()
					if confirmation != "REVOKE":
						print("Admin provisioning cancelled.", file=sys.stderr)
						return 1
					for other_admin in other_admins:
						other_admin.role = "user"
				if existing_user.role != "admin":
					if input("Promote the existing owner account to admin? Type yes to confirm: ").strip().lower() != "yes":
						print("Admin provisioning cancelled.", file=sys.stderr)
						return 1
				existing_user.role = "admin"
				db.commit()
				print("The configured owner account is now the sole administrator.")
				return 0
	except ValueError as exc:
		print(str(exc), file=sys.stderr)
		return 1
	except SQLAlchemyError:
		print("Admin provisioning failed. Check database connectivity.", file=sys.stderr)
		return 1

	full_name = input("Admin full name: ").strip()
	password = getpass("Admin password: ")
	password_confirmation = getpass("Confirm admin password: ")
	if password != password_confirmation:
		print("Passwords do not match.", file=sys.stderr)
		return 1

	try:
		admin_data = AdminCreate(full_name=full_name, email=email, password=password)
	except ValidationError as exc:
		messages = "; ".join(error["msg"] for error in exc.errors(include_input=False))
		print(f"Invalid admin details: {messages}", file=sys.stderr)
		return 1

	try:
		with SessionLocal() as db:
			admin = create_admin_user(db, admin_data)
	except ValueError as exc:
		print(str(exc), file=sys.stderr)
		return 1
	except SQLAlchemyError:
		print("Admin creation failed. Check database connectivity and migration status.", file=sys.stderr)
		return 1

	print("Created the configured admin owner account.")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())