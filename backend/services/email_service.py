from email.message import EmailMessage
import smtplib
import ssl

from backend.config import get_settings


def send_password_reset_email(recipient: str, reset_url: str | None) -> None:
	settings = get_settings()
	if not all((settings.SMTP_HOST, settings.SMTP_USERNAME, settings.SMTP_PASSWORD, settings.SMTP_FROM_EMAIL)):
		raise RuntimeError("SMTP password-reset delivery is not configured")

	message = EmailMessage()
	message["Subject"] = "Reset your FINPATH password"
	message["From"] = settings.SMTP_FROM_EMAIL
	message["To"] = recipient
	body = "We received a request for FINPATH password-reset instructions.\n\n"
	if reset_url:
		body += (
			f"Reset your password here: {reset_url}\n\n"
			"This link expires soon and can be used only once. "
		)
	else:
		body += (
			"For security, this message cannot confirm whether the address is associated "
			"with an active account. If you did not request a reset, you can ignore this email.\n\n"
		)
	body += "If you did not request this, you can ignore this email."
	message.set_content(body)

	context = ssl.create_default_context()
	with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
		if settings.SMTP_USE_TLS:
			server.starttls(context=context)
		server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
		server.send_message(message)


def password_reset_email_configured() -> bool:
	settings = get_settings()
	return all((settings.SMTP_HOST, settings.SMTP_USERNAME, settings.SMTP_PASSWORD, settings.SMTP_FROM_EMAIL))