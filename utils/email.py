from html import escape

# from mailjet_rest import Client

from core.config import settings
from logger import logger

import base64
import smtplib

from email.message import EmailMessage
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

# ---------------------------------------------------------------------------
# Design tokens (Apple-inspired layout, Evvent brand colours)
# ---------------------------------------------------------------------------

FONT = "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "'SF Mono', SFMono-Regular, Menlo, Consolas, monospace"

# Evvent brand palette
NAV = "#126a97"         # nav bar, footer, brand hover
SURFACE = "#efecd9"     # site body / page background
BRAND = "#1c8cc8"       # buttons, links, accents
BRAND_HOVER = "#126a97" # button hover
BRAND_SOFT = "#e3f1f9"  # soft panels and icon backgrounds
INK = "#10324a"         # text on light backgrounds
WHITE = "#ffffff"       # text on dark backgrounds

# Supporting tints derived from INK so secondary text stays on-brand
GREY = "#3f5b70"        # secondary text
LIGHT = "#6b8294"       # labels, small print
LINE = "#d9e5ec"        # hairline dividers

# Aliases used by the building blocks below
CANVAS = BRAND_SOFT     # soft panels
BLUE = BRAND            # links
GREEN = BRAND           # "Free" total uses the brand colour

SUPPORT_EMAIL = "support@evvent.com"


def _e(value) -> str:
    """Escape user-supplied values before they go into HTML."""
    return escape(str(value), quote=True)


# ---------------------------------------------------------------------------
# Shared layout
# ---------------------------------------------------------------------------

def _wrap(body_html: str, preheader: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="color-scheme" content="light" />
  <meta name="supported-color-schemes" content="light" />
  <title>Evvent</title>
  <style>
    body {{ margin:0; padding:0; -webkit-text-size-adjust:100%; -ms-text-size-adjust:100%; }}
    table {{ border-collapse:collapse; }}
    a {{ color:{BRAND}; text-decoration:none; }}
    .btn {{ background-color:{BRAND} !important; }}
    .btn:hover {{ background-color:{BRAND_HOVER} !important; }}
    @media only screen and (max-width:600px) {{
      .outer {{ padding:0 !important; }}
      .nav, .foot, .card {{ border-radius:0 !important; }}
      .nav {{ padding:20px 24px !important; }}
      .inner {{ padding:40px 24px !important; }}
      .foot {{ padding:28px 24px !important; }}
      .h1 {{ font-size:28px !important; line-height:34px !important; }}
      .ref {{ font-size:22px !important; letter-spacing:2px !important; }}
    }}
  </style>
</head>
<body style="margin:0;padding:0;background-color:{SURFACE};">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;mso-hide:all;">{_e(preheader)}</div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{SURFACE};">
    <tr>
      <td class="outer" align="center" style="padding:40px 16px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;">
          <tr>
            <td class="nav" style="background-color:{NAV};border-radius:18px 18px 0 0;padding:22px 48px;font-family:{FONT};">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td style="font-family:{FONT};font-size:22px;font-weight:700;letter-spacing:-0.4px;color:{WHITE};">Evvent</td>
                  <td align="right" style="font-family:{FONT};font-size:12px;color:{BRAND_SOFT};">Discover experiences</td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td class="card" style="background-color:{WHITE};">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td class="inner" style="padding:52px 48px;font-family:{FONT};color:{INK};">
                    {body_html}
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td class="foot" align="center" style="background-color:{NAV};border-radius:0 0 18px 18px;padding:32px 48px;font-family:{FONT};font-size:12px;line-height:19px;color:{WHITE};">
              Need help? Contact us at <a href="mailto:{SUPPORT_EMAIL}" style="color:{WHITE};text-decoration:underline;">{SUPPORT_EMAIL}</a><br />
              <span style="color:{BRAND_SOFT};">You received this email because you have an account or booking with Evvent.</span><br /><br />
              Copyright &copy; 2026 Evvent. All rights reserved.
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------

def _heading(text_html: str) -> str:
    return (
        f'<h1 class="h1" style="margin:0 0 12px;font-family:{FONT};font-size:34px;line-height:40px;'
        f'font-weight:600;letter-spacing:-0.6px;color:{INK};text-align:center;">{text_html}</h1>'
    )


def _lead(text_html: str) -> str:
    return (
        f'<p style="margin:0 0 36px;font-family:{FONT};font-size:17px;line-height:26px;'
        f'color:{GREY};text-align:center;">{text_html}</p>'
    )


def _p(text_html: str, *, center: bool = False) -> str:
    align = "center" if center else "left"
    return (
        f'<p style="margin:0 0 16px;font-family:{FONT};font-size:15px;line-height:24px;'
        f'color:{INK};text-align:{align};">{text_html}</p>'
    )


def _note(text_html: str) -> str:
    return (
        f'<p style="margin:0;font-family:{FONT};font-size:13px;line-height:20px;'
        f'color:{LIGHT};text-align:center;">{text_html}</p>'
    )


def _label(text: str) -> str:
    return (
        f'<p style="margin:0 0 12px;font-family:{FONT};font-size:12px;font-weight:600;'
        f'letter-spacing:0.6px;text-transform:uppercase;color:{LIGHT};">{text}</p>'
    )


def _divider() -> str:
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">'
        f'<tr><td style="padding:32px 0;"><div style="height:1px;line-height:1px;font-size:1px;background-color:{LINE};">&nbsp;</div></td></tr>'
        "</table>"
    )


def _panel(inner_html: str, *, padding: str = "28px 24px") -> str:
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">'
        f'<tr><td style="background-color:{CANVAS};border-radius:12px;padding:{padding};font-family:{FONT};">'
        f"{inner_html}</td></tr></table>"
    )


def _rows(rows: list[tuple[str, str]]) -> str:
    """Receipt-style label / value rows separated by hairlines. Values must be pre-escaped."""
    html = '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">'
    for i, (label, value) in enumerate(rows):
        border = "" if i == 0 else f"border-top:1px solid {LINE};"
        html += (
            "<tr>"
            f'<td valign="top" style="{border}padding:14px 16px 14px 0;font-family:{FONT};font-size:14px;'
            f'line-height:20px;color:{GREY};white-space:nowrap;">{label}</td>'
            f'<td valign="top" align="right" style="{border}padding:14px 0;font-family:{FONT};font-size:14px;'
            f'line-height:20px;color:{INK};font-weight:500;">{value}</td>'
            "</tr>"
        )
    return html + "</table>"


def _button(label: str, href: str) -> str:
    """Centred pill button in the brand colour (hover handled by the .btn class)."""
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center" style="margin:0 auto;">'
        f'<tr><td class="btn" align="center" style="background-color:{BRAND};border-radius:24px;">'
        f'<a href="{_e(href)}" style="display:inline-block;padding:14px 30px;font-family:{FONT};font-size:15px;'
        f'font-weight:600;color:{WHITE};text-decoration:none;border-radius:24px;">{label}</a>'
        "</td></tr></table>"
    )


def _app_url() -> str | None:
    """Optional link to the web app; set FRONTEND_URL in settings to show call-to-action buttons."""
    return getattr(settings, "FRONTEND_URL", None)


# ---------------------------------------------------------------------------
# Template renderers
# ---------------------------------------------------------------------------

def _render_welcome_email(first_name: str) -> tuple[str, str, str]:
    subject = f"Welcome to Evvent, {first_name}"

    text_body = (
        f"Hi {first_name},\n\n"
        "Welcome to Evvent. Your account is ready.\n"
        "Discover events near you, book tickets in seconds, or host your own.\n\n"
        f"Questions? Reply to this email or write to {SUPPORT_EMAIL}.\n\n"
        "The Evvent Team"
    )

    name = _e(first_name)
    features = [
        ("Discover", "Find what's happening near you."),
        ("Book", "Get tickets in a few taps."),
        ("Host", "Create and sell tickets to your own events."),
    ]
    feature_rows = ""
    for i, (title, desc) in enumerate(features, start=1):
        border = "" if i == 1 else f"border-top:1px solid {LINE};"
        feature_rows += (
            "<tr>"
            f'<td valign="top" width="52" style="{border}padding:18px 0;">'
            f'<div style="width:38px;height:38px;line-height:38px;border-radius:50%;background-color:{BRAND_SOFT};'
            f'color:{BRAND};font-family:{FONT};font-size:15px;font-weight:700;text-align:center;">{i}</div></td>'
            f'<td valign="middle" style="{border}padding:18px 0;font-family:{FONT};">'
            f'<div style="font-size:15px;line-height:22px;font-weight:600;color:{INK};">{title}</div>'
            f'<div style="font-size:14px;line-height:20px;color:{GREY};">{desc}</div>'
            "</td></tr>"
        )

    url = _app_url()
    cta = (
        '<div style="height:32px;line-height:32px;font-size:1px;">&nbsp;</div>' + _button("Explore events", url)
        if url
        else ""
    )

    body_html = (
        _heading(f"Welcome to Evvent,<br />{name}.")
        + _lead("Your account is ready. Great experiences are a few taps away.")
        + '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">'
        + f"{feature_rows}</table>"
        + cta
        + _divider()
        + _note(
            "Questions? Just reply to this email.<br />"
            f'<a href="mailto:{SUPPORT_EMAIL}" style="color:{BLUE};text-decoration:none;">{SUPPORT_EMAIL}</a>'
        )
    )

    return subject, text_body, _wrap(body_html, preheader="Your Evvent account is ready.")


def _render_forgot_password_email(
    first_name: str,
    reset_token: str,
    expires_minutes: int,
) -> tuple[str, str, str]:
    subject = "Reset your Evvent password"

    text_body = (
        f"Hi {first_name},\n\n"
        "We received a request to reset your Evvent password.\n"
        f"Your reset code is: {reset_token}\n\n"
        f"This code expires in {expires_minutes} minutes.\n"
        "If you didn't request this, you can ignore this email. Your password will not change.\n\n"
        "The Evvent Team"
    )

    body_html = (
        _heading("Reset your password.")
        + _lead(
            f"Hi {_e(first_name)}, enter this code in the app to set a new password. "
            f"It expires in {int(expires_minutes)} minutes."
        )
        + _panel(
            f'<div class="ref" style="font-family:{MONO};font-size:30px;line-height:36px;font-weight:600;'
            f'letter-spacing:6px;color:{BRAND};text-align:center;">{_e(reset_token)}</div>',
            padding="28px 16px",
        )
        + _divider()
        + _note("Didn't request this? You can safely ignore this email. Your password will not change.")
    )

    return subject, text_body, _wrap(body_html, preheader=f"Your reset code expires in {expires_minutes} minutes.")


def _render_password_reset_success_email(first_name: str) -> tuple[str, str, str]:
    subject = "Your Evvent password was changed"

    text_body = (
        f"Hi {first_name},\n\n"
        "Your Evvent password was changed successfully.\n"
        f"If you didn't make this change, contact us right away at {SUPPORT_EMAIL}.\n\n"
        "The Evvent Team"
    )

    body_html = (
        _heading("Your password was changed.")
        + _lead(f"Hi {_e(first_name)}, you can now sign in to Evvent with your new password.")
        + _panel(
            _p(
                "Didn't make this change? Contact us right away at "
                f'<a href="mailto:{SUPPORT_EMAIL}" style="color:{BLUE};text-decoration:none;">{SUPPORT_EMAIL}</a> '
                "so we can secure your account.",
                center=True,
            ).replace("margin:0 0 16px", "margin:0")
        )
    )

    return subject, text_body, _wrap(body_html, preheader="Your Evvent password was updated.")


def _qr_block(cid: str = "evvent_qr") -> str:
    """Centred QR code image block. References the image by CID (inline attachment)."""
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">'
        f'<tr><td align="center" style="padding:24px 0;">'
        f'<img src="cid:{cid}" width="160" height="160" '
        f'alt="Ticket QR Code" style="display:block;border:0;border-radius:8px;" />'
        f'<div style="margin-top:8px;font-family:{FONT};font-size:11px;color:{LIGHT};">Scan at the entrance</div>'
        "</td></tr></table>"
    )


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
    qr_code_base64: str | None = None,
) -> tuple[str, str, str]:
    subject = f"You're going to {event_title}"

    is_free = total_amount == 0
    amount_display = "Free" if is_free else f"₦{total_amount / 100:,.2f}"
    ticket_word = "ticket" if quantity == 1 else "tickets"

    text_body = (
        f"Hi {attendee_name},\n\n"
        f"Your booking for '{event_title}' is confirmed.\n\n"
        f"Booking Ref: {order_ref}\n"
        f"Date: {event_date}\n"
        f"Location: {event_location}\n"
        f"Duration: {event_duration}\n"
        f"Ticket: {ticket_type_name} x {quantity}\n"
        f"Total: {amount_display}\n\n"
        "Show your QR code or booking reference at the entrance.\n\n"
        "See you there,\nThe Evvent Team"
    )

    total_html = (
        f'<span style="color:{GREEN};font-weight:600;">Free</span>'
        if is_free
        else f'<span style="font-weight:600;">{amount_display}</span>'
    )

    details = _rows([
        ("Date &amp; time", _e(event_date)),
        ("Location", _e(event_location)),
        ("Duration", _e(event_duration)),
        ("Ticket", f"{_e(ticket_type_name)} &times; {int(quantity)}"),
        ("Total", total_html),
    ])

    attendees = _rows([
        (
            f'<span style="color:{INK};font-weight:500;">{_e(att.get("name", ""))}</span>',
            f'<span style="color:{GREY};font-weight:400;">{_e(att.get("email", ""))}</span>',
        )
        for att in all_attendees
    ])

    qr_section = (
        _divider()
        + _label("Your ticket QR code")
        + _qr_block()
        if qr_code_base64
        else ""
    )

    body_html = (
        _heading(f"You're going to<br />{_e(event_title)}.")
        + _lead(f"Hi {_e(attendee_name)}, your booking is confirmed. {int(quantity)} {ticket_word}, all set.")
        + '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">'
        f'<tr><td style="background-color:{NAV};border-radius:14px;padding:26px 24px;font-family:{FONT};">'
        f'<div style="font-size:12px;font-weight:600;letter-spacing:0.6px;text-transform:uppercase;'
        f'color:{BRAND_SOFT};text-align:center;margin-bottom:8px;">Booking reference</div>'
        f'<div class="ref" style="font-family:{MONO};font-size:26px;line-height:32px;font-weight:600;'
        f'letter-spacing:3px;color:{WHITE};text-align:center;">{_e(order_ref)}</div>'
        "</td></tr></table>"
        + '<div style="height:32px;line-height:32px;font-size:1px;">&nbsp;</div>'
        + _label("Event details")
        + details
        + _divider()
        + _label("Attendees")
        + attendees
        + qr_section
        + _divider()
        + _note("Keep this email. Present your QR code or booking reference at the entrance.")
    )

    return subject, text_body, _wrap(body_html, preheader=f"Booking {order_ref} confirmed for {event_title}.")


# ---------------------------------------------------------------------------
# Organizer booking notification
# ---------------------------------------------------------------------------

def _render_organizer_booking_notification_email(
    *,
    organizer_name: str,
    event_title: str,
    event_date: str,
    buyer_name: str,
    buyer_email: str,
    ticket_type_name: str,
    quantity: int,
    total_amount: int,  # in kobo; 0 = free
    order_ref: str,
) -> tuple[str, str, str]:
    subject = f"New booking for {event_title}"

    is_free = total_amount == 0
    amount_display = "Free" if is_free else f"₦{total_amount / 100:,.2f}"
    ticket_word = "ticket" if quantity == 1 else "tickets"

    text_body = (
        f"Hi {organizer_name},\n\n"
        f"Great news! {buyer_name} just booked {quantity} {ticket_word} for '{event_title}'.\n\n"
        f"Booking Ref: {order_ref}\n"
        f"Buyer: {buyer_name} ({buyer_email})\n"
        f"Ticket: {ticket_type_name} x {quantity}\n"
        f"Total: {amount_display}\n\n"
        "Log in to your Evvent dashboard to view all bookings.\n\n"
        "The Evvent Team"
    )

    total_html = (
        f'<span style="color:{GREEN};font-weight:600;">Free</span>'
        if is_free
        else f'<span style="font-weight:600;">{amount_display}</span>'
    )

    details = _rows([
        ("Event", _e(event_title)),
        ("Date &amp; time", _e(event_date)),
        ("Buyer", f'{_e(buyer_name)} &lt;<a href="mailto:{_e(buyer_email)}" style="color:{BLUE};">{_e(buyer_email)}</a>&gt;'),
        ("Ticket", f"{_e(ticket_type_name)} &times; {int(quantity)}"),
        ("Revenue", total_html),
    ])

    body_html = (
        _heading("New booking!")
        + _lead(
            f"Hi {_e(organizer_name)}, someone just booked {int(quantity)} {ticket_word} "
            f"for <strong>{_e(event_title)}</strong>."
        )
        + '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">'
        f'<tr><td style="background-color:{NAV};border-radius:14px;padding:26px 24px;font-family:{FONT};">'
        f'<div style="font-size:12px;font-weight:600;letter-spacing:0.6px;text-transform:uppercase;'
        f'color:{BRAND_SOFT};text-align:center;margin-bottom:8px;">Booking reference</div>'
        f'<div class="ref" style="font-family:{MONO};font-size:26px;line-height:32px;font-weight:600;'
        f'letter-spacing:3px;color:{WHITE};text-align:center;">{_e(order_ref)}</div>'
        "</td></tr></table>"
        + '<div style="height:32px;line-height:32px;font-size:1px;">&nbsp;</div>'
        + _label("Booking details")
        + details
        + _divider()
        + _note("Log in to your Evvent dashboard to manage all bookings for this event.")
    )

    return subject, text_body, _wrap(body_html, preheader=f"New booking {order_ref} for {event_title}.")


def send_organizer_booking_notification_email(
    *,
    to_email: str,
    organizer_name: str,
    event_title: str,
    event_date: str,
    buyer_name: str,
    buyer_email: str,
    ticket_type_name: str,
    quantity: int,
    total_amount: int,
    order_ref: str,
) -> None:
    subject, text_body, html_body = _render_organizer_booking_notification_email(
        organizer_name=organizer_name,
        event_title=event_title,
        event_date=event_date,
        buyer_name=buyer_name,
        buyer_email=buyer_email,
        ticket_type_name=ticket_type_name,
        quantity=quantity,
        total_amount=total_amount,
        order_ref=order_ref,
    )
    _send(to_email, organizer_name, subject, text_body, html_body, log_label="organizer booking notification email")


# ---------------------------------------------------------------------------
# sender
# ---------------------------------------------------------------------------

def _send(
    to_email: str,
    to_name: str,
    subject: str,
    text_body: str,
    html_body: str,
    *,
    log_label: str,
    inline_images: dict[str, bytes] | None = None,
) -> None:
    """
    Send an email via SMTP.

    ``inline_images`` maps CID names (e.g. ``"evvent_qr"``) to raw PNG bytes.
    The HTML should reference them as ``<img src="cid:evvent_qr">``.
    When provided the message is built as ``multipart/related`` so the images
    are embedded and rendered by all major email clients (including Gmail).
    """
    if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        raise RuntimeError("SMTP credentials are not configured")

    from_addr = formataddr((settings.SMTP_FROM_NAME, settings.SMTP_FROM_EMAIL))
    to_addr = formataddr((to_name, to_email))

    if inline_images:
        # Build multipart/related so CID-referenced images render in all clients
        outer = MIMEMultipart("related")
        outer["Subject"] = subject
        outer["From"] = from_addr
        outer["To"] = to_addr

        alt = MIMEMultipart("alternative")
        outer.attach(alt)
        alt.attach(MIMEText(text_body, "plain"))
        alt.attach(MIMEText(html_body, "html"))

        for cid, img_bytes in inline_images.items():
            img = MIMEImage(img_bytes, "png")
            img.add_header("Content-ID", f"<{cid}>")
            img.add_header("Content-Disposition", "inline", filename=f"{cid}.png")
            outer.attach(img)

        message = outer
    else:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = from_addr
        message["To"] = to_addr
        message.set_content(text_body)
        message.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            timeout=30,
        ) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(
                settings.SMTP_USERNAME,
                settings.SMTP_PASSWORD.replace(" ", ""),
            )
            server.send_message(message)

        logger.info(
            "%s accepted by Gmail SMTP for %s",
            log_label,
            to_email,
        )

    except Exception:
        logger.exception(
            "%s failed for recipient %s",
            log_label,
            to_email,
        )
        raise

# ---------------------------------------------------------------------------
# Public helpers (signatures unchanged)
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
    subject, text_body, html_body = _render_forgot_password_email(first_name, reset_token, expires_minutes)
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
    qr_code_base64: str | None = None,
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
        qr_code_base64=qr_code_base64,
    )
    inline_images = (
        {"evvent_qr": base64.b64decode(qr_code_base64)} if qr_code_base64 else None
    )
    _send(
        to_email,
        attendee_name,
        subject,
        text_body,
        html_body,
        log_label="booking confirmation email",
        inline_images=inline_images,
    )