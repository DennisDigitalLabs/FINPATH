"""Bootstrap the configured admin owner from a trusted operator shell."""

import hmac
import sys
from getpass import getpass

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from backend.config import get_settings
from backend.database import SessionLocal
from backend.models import User
from backend.schemas.user import AdminCreate
from backend.services.admin_bootstrap_service import provision_configured_owner
from backend.services.auth_service import normalize_email


def _validated_owner_email(value: str) -> str:
	try:
		return normalize_email(str(TypeAdapter(EmailStr).validate_python(value)))
	except ValidationError as exc:
		raise ValueError("ADMIN_OWNER_EMAIL must be a valid email address.") from exc


def _read_owner_data(email: str, existing: User | None) -> AdminCreate:
	if existing is None:
		full_name = input("Admin full name: ").strip()
	else:
		full_name = input(
			"Admin full name (leave blank to keep the current name): "
		).strip() or existing.full_name

	password = getpass("Admin password: ")
	password_confirmation = getpass("Confirm admin password: ")
	if password != password_confirmation:
		raise ValueError("Passwords do not match.")
	return AdminCreate(full_name=full_name, email=email, password=password)


def main() -> int:
	settings = get_settings()
	try:
		owner_email = _validated_owner_email(settings.ADMIN_OWNER_EMAIL)
	except (ValidationError, ValueError):
		print(
			"Set a valid ADMIN_OWNER_EMAIL before bootstrapping the owner.",
			file=sys.stderr,
		)
		return 1

	bootstrap_token = settings.ADMIN_BOOTSTRAP_TOKEN
	if len(bootstrap_token) < 32:
		print(
			"Set a temporary ADMIN_BOOTSTRAP_TOKEN of at least 32 characters.",
			file=sys.stderr,
		)
		return 1

	if normalize_email(input("Configured owner email: ")) != owner_email:
		print(
			"The supplied email does not match ADMIN_OWNER_EMAIL.",
			file=sys.stderr,
		)
		return 1
	if not hmac.compare_digest(
		getpass("Bootstrap token: "),
		bootstrap_token,
	):
		print("Bootstrap authorization failed.", file=sys.stderr)
		return 1

	try:
		with SessionLocal() as db:
			matches = (
				db.query(User)
				.filter(func.lower(User.email) == owner_email)
				.limit(2)
				.all()
			)
			if len(matches) > 1:
				raise ValueError(
					"Multiple accounts match ADMIN_OWNER_EMAIL. "
					"Resolve the duplicate records through a trusted "
					"operator process before bootstrapping."
				)
			existing_owner = matches[0] if matches else None
			if existing_owner is not None:
				if existing_owner.is_active and existing_owner.role == "admin":
					raise ValueError(
						"The configured administrator is already established; "
						"bootstrap is disabled."
					)

			repair_existing = existing_owner is not None
			if repair_existing:
				confirmation = input(
					"The configured owner account is inactive or has an "
					"inconsistent role. To restore only this configured "
					"account and set a new password, type REPAIR OWNER: "
				).strip()
				if confirmation != "REPAIR OWNER":
					print("Owner repair cancelled.", file=sys.stderr)
					return 1

			try:
				owner_data = _read_owner_data(owner_email, existing_owner)
			except ValidationError as exc:
				messages = "; ".join(
					error["msg"] for error in exc.errors(include_input=False)
				)
				print(f"Invalid owner details: {messages}", file=sys.stderr)
				return 1
			except ValueError as exc:
				print(str(exc), file=sys.stderr)
				return 1

			provision_configured_owner(
				db,
				owner_data,
				repair_existing=repair_existing,
			)
	except ValueError as exc:
		print(str(exc), file=sys.stderr)
		return 1
	except SQLAlchemyError:
		print(
			"Owner bootstrap failed. Check database connectivity and "
			"migration status.",
			file=sys.stderr,
		)
		return 1

	if repair_existing:
		print(
			"The configured owner account was restored with the supplied "
			"password."
		)
	else:
		print("Created the configured administrator owner account.")
	print(
		"Remove ADMIN_BOOTSTRAP_TOKEN from the deployment environment, "
		"then sign in with the configured owner email and supplied password."
	)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
