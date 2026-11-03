from dotenv import load_dotenv
load_dotenv()

from utils.email import send_welcome_email, send_booking_confirmation_email
from utils.qrcode_util import generate_qr_code_base64

# ── Welcome email ────────────────────────────────────────────────────────────
send_welcome_email(
    to_email="ewherheakpesiri+108@gmail.com",
    first_name="James",
)
print("Welcome email sent.")

# ── Booking confirmation with QR code ────────────────────────────────────────
qr = generate_qr_code_base64("C6ED8824-E4CA-44F4-9587-B284EAF128AF")

send_booking_confirmation_email(
    to_email="ewherheakpesiri+108@gmail.com",
    attendee_name="James Ede",
    event_title="Lagos Tech Summit 2026",
    event_date="Saturday, November 7 2026 · 10:00 AM",
    event_location="Eko Hotel, Lagos",
    event_duration="6 hours",
    ticket_type_name="Regular",
    quantity=2,
    total_amount=1000000,   # ₦10,000.00 in kobo
    order_ref="C6ED8824",
    all_attendees=[
        {"name": "James Ede", "email": "ewherheakpesiri+108@gmail.com"},
        {"name": "Ada Obi",   "email": "ada@example.com"},
    ],
    qr_code_base64=qr,
)
print("Booking confirmation email sent.")
