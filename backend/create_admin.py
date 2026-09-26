"""Run with ``python -m backend.create_admin`` after database migrations."""

import sys
from getpass import getpass

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from backend.database import SessionLocal
from backend.schemas.user import AdminCreate
from backend.services.auth_service import count_admin_users, create_admin_user


def main() -> int:
	email = input("Admin email: ").strip()
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
			if count_admin_users(db) > 0:
				raise ValueError("An active admin already exists; use the authenticated admin API for additional admins.")
			admin = create_admin_user(db, admin_data)
	except ValueError as exc:
		print(str(exc), file=sys.stderr)
		return 1
	except SQLAlchemyError:
		print("Admin creation failed. Check database connectivity and migration status.", file=sys.stderr)
		return 1

	print(f"Created initial admin account for {admin.email}.")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())