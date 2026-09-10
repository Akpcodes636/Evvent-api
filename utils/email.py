from email.message import EmailMessage
import smtplib

from core.config import settings
from logger import logger


def _render_welcome_email(first_name: str) -> tuple[str, str, str]:
    subject = "Welcome to Evvent!"
    text_body = (
        f"Hi {first_name},\n\n"
        "Welcome to Evvent! Your account has been created successfully.\n"
        "You can now log in and start browsing or creating events.\n\n"
        "See you there,\nThe Evvent Team"
    )
    html_body = f"""\
<html>
  <body style="font-family: Arial, sans-serif; color: #1a1a1a; line-height: 1.5;">
    <h2>Welcome to Evvent, {first_name}!</h2>
    <p>Your account has been created successfully.</p>
    <p>You can now log in and start browsing or creating events.</p>
    <p>See you there,<br>The Evvent Team</p>
  </body>
</html>
"""
    return subject, text_body, html_body


def _render_password_reset_email(first_name: str, reset_token: str, expires_minutes: int) -> tuple[str, str, str]:
    subject = "Reset your Evvent password"
    text_body = (
        f"Hi {first_name},\n\n"
        "We received a request to reset your Evvent password.\n"
        f"Your reset code is: {reset_token}\n\n"
        f"This code expires in {expires_minutes} minutes.\n"
        "If you didn't request this, you can safely ignore this email.\n\n"
        "The Evvent Team"
    )
    html_body = f"""\
<html>
  <body style="font-family: Arial, sans-serif; color: #1a1a1a; line-height: 1.5;">
    <h2>Reset your password</h2>
    <p>Hi {first_name},</p>
    <p>We received a request to reset your Evvent password.</p>
    <p>Your reset code is:</p>
    <p style="font-size: 20px; font-weight: bold; letter-spacing: 1px;">{reset_token}</p>
    <p>This code expires in {expires_minutes} minutes.</p>
    <p>If you didn't request this, you can safely ignore this email.</p>
    <p>The Evvent Team</p>
  </body>
</html>
"""
    return subject, text_body, html_body


def _send(
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str,
    *,
    log_label: str
) -> None:
    if not settings.SMTP_HOST:
        logger.warning(
            "SMTP_HOST not configured; skipping %s to %s",
            log_label,
            to_email
        )
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = (
        f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    )
    message["To"] = to_email
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            timeout=10,
        ) as smtp:
            smtp.ehlo()

            if settings.SMTP_USE_TLS:
                smtp.starttls()
                smtp.ehlo()

            smtp.login(
                settings.SMTP_USERNAME,
                settings.SMTP_PASSWORD,
            )

            smtp.send_message(message)

        logger.info(
            "%s sent to %s",
            log_label,
            to_email
        )

    except Exception:
        logger.exception(
            "Failed to send %s to %s",
            log_label,
            to_email
        )

def send_welcome_email(to_email: str, first_name: str) -> None:
    subject, text_body, html_body = _render_welcome_email(first_name)
    _send(to_email, subject, text_body, html_body, log_label="welcome email")


def send_password_reset_email(to_email: str, first_name: str, reset_token: str, expires_minutes: int) -> None:
    subject, text_body, html_body = _render_password_reset_email(first_name, reset_token, expires_minutes)
    _send(to_email, subject, text_body, html_body, log_label="password reset email")
