from mailjet_rest import Client

from core.config import settings
from logger import logger

# ---------------------------------------------------------------------------
# Shared HTML layout
# ---------------------------------------------------------------------------

_BASE_STYLE = """
  body { margin: 0; padding: 0; background-color: #f0eeff; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #3d3d3d; }
  table { border-collapse: collapse; }
  .wrapper { width: 100%; background-color: #f0eeff; padding: 32px 0; }
  .card { max-width: 580px; margin: 0 auto; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 8px 40px rgba(108,71,255,0.12); }
  .header { background: linear-gradient(135deg, #4f23e0 0%, #7c3aed 50%, #a855f7 100%); padding: 40px 40px 32px; text-align: center; position: relative; }
  .header-logo { font-size: 30px; font-weight: 900; color: #ffffff; letter-spacing: -0.5px; margin-bottom: 6px; }
  .header-logo span { color: #ddd6fe; }
  .header-tagline { font-size: 13px; color: rgba(255,255,255,0.7); letter-spacing: 1px; text-transform: uppercase; }
  .header-icon { font-size: 52px; margin-bottom: 12px; display: block; }
  .body { padding: 40px 40px 32px; }
  .body h1 { margin: 0 0 12px; font-size: 24px; font-weight: 800; color: #1a0a40; line-height: 1.3; }
  .body h2 { margin: 0 0 10px; font-size: 13px; font-weight: 700; color: #7c3aed; text-transform: uppercase; letter-spacing: 1px; }
  .body p { margin: 0 0 16px; font-size: 15px; line-height: 1.7; color: #555; }
  .btn { display: inline-block; margin: 8px 0 24px; padding: 15px 36px; background: linear-gradient(135deg, #4f23e0 0%, #a855f7 100%); color: #ffffff !important; font-size: 15px; font-weight: 700; text-decoration: none; border-radius: 50px; letter-spacing: 0.3px; }
  .token-box { display: inline-block; margin: 8px 0 24px; padding: 16px 32px; background-color: #f5f0ff; border: 2px dashed #7c3aed; border-radius: 12px; font-size: 28px; font-weight: 800; letter-spacing: 6px; color: #4f23e0; }
  .divider { border: none; border-top: 1px solid #f0eeff; margin: 28px 0; }
  .footer { padding: 24px 40px; text-align: center; font-size: 12px; color: #bbb; background-color: #fafafa; }
  .footer a { color: #7c3aed; text-decoration: none; }
  .highlight-box { background: linear-gradient(135deg, #f5f0ff 0%, #fdf4ff 100%); border-left: 4px solid #7c3aed; border-radius: 0 12px 12px 0; padding: 20px 24px; margin: 20px 0; }
  .highlight-box p { margin: 0; color: #3d2a7a; font-weight: 500; }
  .ticket-card { background: #1a0a40; border-radius: 12px; padding: 24px; margin: 20px 0; color: #fff; position: relative; overflow: hidden; }
  .ticket-card::before { content: ""; position: absolute; top: -30px; right: -30px; width: 120px; height: 120px; background: rgba(168,85,247,0.2); border-radius: 50%; }
  .ticket-card::after { content: ""; position: absolute; bottom: -40px; left: -20px; width: 100px; height: 100px; background: rgba(79,35,224,0.2); border-radius: 50%; }
  .ticket-label { font-size: 11px; font-weight: 700; color: rgba(255,255,255,0.5); text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 4px; }
  .ticket-value { font-size: 16px; font-weight: 700; color: #fff; margin-bottom: 16px; }
  .ticket-ref { font-size: 20px; font-weight: 900; color: #a78bfa; letter-spacing: 2px; font-family: monospace; }
  .info-row { display: table; width: 100%; margin-bottom: 12px; }
  .info-icon { display: table-cell; width: 36px; vertical-align: top; font-size: 18px; padding-top: 2px; }
  .info-text { display: table-cell; vertical-align: top; font-size: 14px; color: #444; line-height: 1.5; }
  .info-text strong { color: #1a0a40; display: block; font-size: 13px; }
  .attendee-row { background: #fafafe; border: 1px solid #ede9ff; border-radius: 8px; padding: 12px 16px; margin-bottom: 8px; font-size: 14px; color: #444; }
  .attendee-num { display: inline-block; width: 24px; height: 24px; background: linear-gradient(135deg, #4f23e0, #a855f7); color: #fff; border-radius: 50%; text-align: center; line-height: 24px; font-size: 12px; font-weight: 700; margin-right: 8px; }
  .feature-grid { display: table; width: 100%; margin: 20px 0; }
  .feature-item { display: table-cell; width: 33%; text-align: center; padding: 16px 8px; }
  .feature-emoji { font-size: 28px; display: block; margin-bottom: 8px; }
  .feature-text { font-size: 13px; color: #666; font-weight: 500; }
  .social-row { text-align: center; margin: 16px 0; }
  .social-row a { display: inline-block; margin: 0 6px; font-size: 12px; color: #7c3aed; text-decoration: none; font-weight: 600; }
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
    subject = f"You're in, {first_name}! Welcome to Evvent 🎉"

    text_body = (
        f"Hi {first_name},\n\n"
        "Welcome to Evvent — your all-access pass to unforgettable experiences!\n"
        "Your account is ready. Explore events, book tickets in seconds, or create your own.\n\n"
        "See you at the next great event,\nThe Evvent Team"
    )

    body_html = f"""\
      <div style="text-align:center; margin-bottom:8px;">
        <span style="font-size:56px;">🎊</span>
      </div>
      <h1 style="text-align:center;">You're officially in,<br/>{first_name}!</h1>
      <p style="text-align:center; color:#888; margin-bottom:28px;">
        Welcome to Evvent — your gateway to unforgettable experiences.
      </p>

      <div class="highlight-box">
        <p>✨ Your account is <strong>fully set up</strong> and ready. Dive in and discover what's happening around you.</p>
      </div>

      <table class="feature-grid" role="presentation" width="100%">
        <tr>
          <td class="feature-item">
            <span class="feature-emoji">🎟️</span>
            <div class="feature-text">Book tickets<br/>in seconds</div>
          </td>
          <td class="feature-item">
            <span class="feature-emoji">🗓️</span>
            <div class="feature-text">Discover<br/>nearby events</div>
          </td>
          <td class="feature-item">
            <span class="feature-emoji">🚀</span>
            <div class="feature-text">Create &amp;<br/>host your own</div>
          </td>
        </tr>
      </table>

      <hr class="divider" />

      <p style="font-size:13px; color:#999; text-align:center; margin:0;">
        Questions? Just reply to this email — we're always happy to help.<br/>
        <a href="mailto:support@evvent.com" style="color:#7c3aed;">support@evvent.com</a>
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


def _render_booking_confirmation_email(
    *,
    attendee_name: str,
    event_title: str,
    event_date: str,
    event_location: str,
    event_duration: str,
    ticket_type_name: str,
    quantity: int,
    total_amount: int,  # in kobo; 0 = free
    order_ref: str,
    all_attendees: list[dict],  # [{"name": str, "email": str}]
) -> tuple[str, str, str]:
    subject = f"Your tickets for {event_title} are confirmed! 🎟️"

    is_free = total_amount == 0
    amount_display = "FREE" if is_free else f"₦{total_amount / 100:,.2f}"

    text_body = (
        f"Hi {attendee_name},\n\n"
        f"Your booking for '{event_title}' is confirmed!\n\n"
        f"Date: {event_date}\n"
        f"Location: {event_location}\n"
        f"Duration: {event_duration}\n"
        f"Ticket: {ticket_type_name} × {quantity}\n"
        f"Amount: {amount_display}\n"
        f"Booking Ref: {order_ref}\n\n"
        "See you at the event!\nThe Evvent Team"
    )

    attendees_html = ""
    for i, att in enumerate(all_attendees, start=1):
        attendees_html += f"""\
        <div class="attendee-row">
          <span class="attendee-num">{i}</span>
          <strong style="color:#1a0a40;">{att["name"]}</strong>
          <span style="color:#999; font-size:13px; margin-left:8px;">{att["email"]}</span>
        </div>
"""

    badge_color = "#10b981" if is_free else "#7c3aed"
    badge_label = "FREE EVENT" if is_free else "PAID"

    body_html = f"""\
      <div style="text-align:center; margin-bottom:4px;">
        <span style="font-size:52px;">🎟️</span>
      </div>
      <h1 style="text-align:center; font-size:22px;">You're going to<br/><span style="color:#7c3aed;">{event_title}</span>!</h1>
      <p style="text-align:center; color:#888; margin-bottom:28px; font-size:14px;">
        Hi <strong style="color:#1a0a40;">{attendee_name}</strong> — your booking is confirmed and your spot is secured. 🙌
      </p>

      <div class="ticket-card" role="presentation">
        <div style="position:relative; z-index:1;">
          <div style="display:table; width:100%; margin-bottom:20px;">
            <div style="display:table-cell; vertical-align:middle;">
              <div class="ticket-label">Event</div>
              <div class="ticket-value" style="font-size:18px;">{event_title}</div>
            </div>
            <div style="display:table-cell; text-align:right; vertical-align:top; width:90px;">
              <span style="background:{badge_color}; color:#fff; font-size:10px; font-weight:800; padding:4px 10px; border-radius:20px; text-transform:uppercase; letter-spacing:1px;">{badge_label}</span>
            </div>
          </div>

          <div style="display:table; width:100%;">
            <div style="display:table-cell; width:50%; vertical-align:top; padding-right:12px;">
              <div class="ticket-label">Date &amp; Time</div>
              <div class="ticket-value">{event_date}</div>
              <div class="ticket-label">Duration</div>
              <div class="ticket-value">{event_duration}</div>
            </div>
            <div style="display:table-cell; width:50%; vertical-align:top;">
              <div class="ticket-label">Ticket Type</div>
              <div class="ticket-value">{ticket_type_name}</div>
              <div class="ticket-label">Quantity</div>
              <div class="ticket-value">{quantity} ticket{'s' if quantity > 1 else ''}</div>
            </div>
          </div>

          <div style="border-top:1px dashed rgba(255,255,255,0.2); margin:16px 0; padding-top:16px; display:table; width:100%;">
            <div style="display:table-cell; vertical-align:middle;">
              <div class="ticket-label">Booking Reference</div>
              <div class="ticket-ref">{order_ref}</div>
            </div>
            <div style="display:table-cell; text-align:right; vertical-align:middle; width:120px;">
              <div class="ticket-label" style="text-align:right;">Total Paid</div>
              <div style="font-size:22px; font-weight:900; color:#a78bfa;">{amount_display}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="info-row" style="margin-top:24px;">
        <div class="info-icon">📍</div>
        <div class="info-text"><strong>Location</strong>{event_location}</div>
      </div>

      <hr class="divider" />

      <h2>Attendees</h2>
      {attendees_html}

      <hr class="divider" />

      <div class="highlight-box">
        <p>💡 <strong>Keep this email</strong> as your booking confirmation. Present your booking reference <strong>{order_ref}</strong> at the venue entrance.</p>
      </div>

      <p style="font-size:13px; color:#999; text-align:center; margin-top:24px;">
        Need help? Reach us at <a href="mailto:support@evvent.com" style="color:#7c3aed;">support@evvent.com</a>
      </p>
"""

    return subject, text_body, _wrap("🎟️", body_html)


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


def send_booking_confirmation_email(
    *,
    to_email: str,
    attendee_name: str,
    event_title: str,
    event_date: str,
    event_location: str,
    event_duration: str,
    ticket_type_name: str,
    quantity: int,
    total_amount: int,
    order_ref: str,
    all_attendees: list[dict],
) -> None:
    subject, text_body, html_body = _render_booking_confirmation_email(
        attendee_name=attendee_name,
        event_title=event_title,
        event_date=event_date,
        event_location=event_location,
        event_duration=event_duration,
        ticket_type_name=ticket_type_name,
        quantity=quantity,
        total_amount=total_amount,
        order_ref=order_ref,
        all_attendees=all_attendees,
    )
    _send(to_email, attendee_name, subject, text_body, html_body, log_label="booking confirmation email")
