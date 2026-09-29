from mailjet_rest import Client

from core.config import settings
from logger import logger

# ---------------------------------------------------------------------------
# Shared HTML layout
# ---------------------------------------------------------------------------

_BASE_STYLE = """
  body { margin: 0; padding: 0; background-color: #f4f4f7; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #3d3d3d; }
  table { border-collapse: collapse; }
  .wrapper { width: 100%; background-color: #f4f4f7; padding: 32px 0; }
  .card { max-width: 560px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,0.08); }
  .header { background: linear-gradient(135deg, #6c47ff 0%, #a855f7 100%); padding: 36px 40px; text-align: center; }
  .header-logo { font-size: 28px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px; }
  .header-logo span { color: #e0d0ff; }
  .body { padding: 40px 40px 32px; }
  .body h1 { margin: 0 0 12px; font-size: 22px; font-weight: 700; color: #1a1a2e; }
  .body p { margin: 0 0 16px; font-size: 15px; line-height: 1.65; color: #555; }
  .btn { display: inline-block; margin: 8px 0 24px; padding: 14px 32px; background: linear-gradient(135deg, #6c47ff 0%, #a855f7 100%); color: #ffffff !important; font-size: 15px; font-weight: 600; text-decoration: none; border-radius: 8px; }
  .token-box { display: inline-block; margin: 8px 0 24px; padding: 16px 32px; background-color: #f0ebff; border: 2px dashed #6c47ff; border-radius: 10px; font-size: 28px; font-weight: 800; letter-spacing: 6px; color: #6c47ff; }
  .divider { border: none; border-top: 1px solid #ebebeb; margin: 24px 0; }
  .footer { padding: 24px 40px; text-align: center; font-size: 12px; color: #aaa; background-color: #fafafa; }
  .footer a { color: #6c47ff; text-decoration: none; }
"""


def _wrap(header_icon: str, body_html: str) -> str:
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <style>{_BASE_STYLE}</style>
</head>
<body>
  <div class="wrapper">
    <table class="card" role="presentation" width="560" align="center">
      <tr>
        <td class="header">
          <div class="header-logo">Evv<span>ent</span> {header_icon}</div>
        </td>
      </tr>
      <tr>
        <td class="body">
          {body_html}
        </td>
      </tr>
      <tr>
        <td class="footer">
          &copy; 2026 Evvent &nbsp;&bull;&nbsp; All rights reserved<br />
          You received this email because you have an account on Evvent.
        </td>
      </tr>
    </table>
  </div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Template renderers
# ---------------------------------------------------------------------------

def _render_welcome_email(first_name: str) -> tuple[str, str, str]:
    subject = f"Welcome to Evvent, {first_name}! 🎉"

    text_body = (
        f"Hi {first_name},\n\n"
        "Welcome to Evvent! Your account has been created successfully.\n"
        "Start exploring amazing events or create your own.\n\n"
        "See you there,\nThe Evvent Team"
    )

    body_html = f"""\
      <h1>Welcome aboard, {first_name}! 🎉</h1>
      <p>We're thrilled to have you on <strong>Evvent</strong>. Your account is all set and ready to go.</p>
      <p>Here's what you can do right now:</p>
      <ul style="padding-left:20px; color:#555; font-size:15px; line-height:2;">
        <li>Browse upcoming events near you</li>
        <li>Book tickets in seconds</li>
        <li>Create and manage your own events</li>
      </ul>
      <hr class="divider" />
      <p style="font-size:13px; color:#999;">
        Questions? Just reply to this email — we're always happy to help.
      </p>
"""

    return subject, text_body, _wrap("🎪", body_html)


def _render_forgot_password_email(
    first_name: str,
    reset_token: str,
    expires_minutes: int,
) -> tuple[str, str, str]:
    subject = "Reset your Evvent password"

    text_body = (
        f"Hi {first_name},\n\n"
        "We received a request to reset your Evvent password.\n"
        f"Your reset token is: {reset_token}\n\n"
        f"This token expires in {expires_minutes} minutes.\n"
        "If you didn't request this, you can safely ignore this email.\n\n"
        "The Evvent Team"
    )

    body_html = f"""\
      <h1>Forgot your password?</h1>
      <p>Hi <strong>{first_name}</strong>,</p>
      <p>No worries — it happens to the best of us. Use the token below to reset your password. It expires in <strong>{expires_minutes} minutes</strong>.</p>
      <div style="text-align:center;">
        <div class="token-box">{reset_token}</div>
      </div>
      <p>Enter this token in the app to set a new password.</p>
      <hr class="divider" />
      <p style="font-size:13px; color:#999;">
        Didn't request a password reset? You can safely ignore this email — your password will not change.
      </p>
"""

    return subject, text_body, _wrap("🔑", body_html)


def _render_password_reset_success_email(first_name: str) -> tuple[str, str, str]:
    subject = "Your Evvent password has been changed"

    text_body = (
        f"Hi {first_name},\n\n"
        "Your Evvent password was successfully changed.\n"
        "If you didn't make this change, please contact us immediately.\n\n"
        "The Evvent Team"
    )

    body_html = f"""\
      <h1>Password changed successfully ✅</h1>
      <p>Hi <strong>{first_name}</strong>,</p>
      <p>Your Evvent account password has been updated successfully. You can now log in with your new password.</p>
      <hr class="divider" />
      <p style="font-size:13px; color:#999;">
        If you did <strong>not</strong> make this change, please contact us immediately at
        <a href="mailto:support@evvent.com">support@evvent.com</a>.
      </p>
"""

    return subject, text_body, _wrap("🔒", body_html)


# ---------------------------------------------------------------------------
# Mailjet sender
# ---------------------------------------------------------------------------

def _send(
    to_email: str,
    to_name: str,
    subject: str,
    text_body: str,
    html_body: str,
    *,
    log_label: str,
) -> None:
    if not settings.MAILJET_APIKEY or not settings.MAILJET_SECRET_KEY:
        logger.warning(
            "MAILJET_APIKEY / MAILJET_SECRET_KEY not configured; skipping %s to %s",
            log_label,
            to_email,
        )
        return

    mailjet = Client(
        auth=(settings.MAILJET_APIKEY, settings.MAILJET_SECRET_KEY),
        version="v3.1",
    )

    data = {
        "Messages": [
            {
                "From": {
                    "Email": settings.MAILJET_FROM_EMAIL,
                    "Name": settings.MAILJET_FROM_NAME,
                },
                "To": [
                    {
                        "Email": to_email,
                        "Name": to_name,
                    }
                ],
                "Subject": subject,
                "TextPart": text_body,
                "HTMLPart": html_body,
            }
        ]
    }

    try:
        result = mailjet.send.create(data=data)
        body = result.json()

        if result.status_code == 200:
            # Log per-message status from Mailjet (Status + MessageID)
            for msg in body.get("Messages", []):
                msg_status = msg.get("Status", "unknown")
                msg_id = (msg.get("To") or [{}])[0].get("MessageID", "n/a")
                if msg_status == "success":
                    logger.info(
                        "%s sent to %s (MessageID: %s)",
                        log_label, to_email, msg_id,
                    )
                else:
                    logger.error(
                        "%s to %s accepted by Mailjet but status=%s — check sender verification. Full msg: %s",
                        log_label, to_email, msg_status, msg,
                    )
        else:
            logger.error(
                "Mailjet HTTP %s for %s to %s: %s",
                result.status_code, log_label, to_email, body,
            )
    except Exception:
        logger.exception(
            "Failed to send %s to %s via Mailjet",
            log_label,
            to_email,
        )


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def send_welcome_email(to_email: str, first_name: str) -> None:
    subject, text_body, html_body = _render_welcome_email(first_name)
    _send(to_email, first_name, subject, text_body, html_body, log_label="welcome email")


def send_password_reset_email(
    to_email: str,
    first_name: str,
    reset_token: str,
    expires_minutes: int,
) -> None:
    subject, text_body, html_body = _render_forgot_password_email(
        first_name, reset_token, expires_minutes
    )
    _send(to_email, first_name, subject, text_body, html_body, log_label="forgot-password email")


def send_password_reset_success_email(to_email: str, first_name: str) -> None:
    subject, text_body, html_body = _render_password_reset_success_email(first_name)
    _send(to_email, first_name, subject, text_body, html_body, log_label="password-reset-success email")
