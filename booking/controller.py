from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, status
from sqlmodel import Session

from auth.dependencies import get_current_user
from booking.schema import (
    AttendeeDetailResponse,
    BookingCreate,
    BookingResponse,
    PaymentRequest,
    PaymentResponse,
    PaystackInitResponse,
)
from booking.services import (
    cancel_booking,
    create_booking,
    get_booking,
    get_booking_attendees,
    initialize_paystack_payment,
    list_user_bookings,
    pay_booking,
    verify_paystack_webhook,
)
from database.session import get_session
from logger import logger
from model.user import User

router = APIRouter(prefix="/bookings", tags=["Bookings"])


# ---------------------------------------------------------------------------
# Create booking (includes attendee details)
# ---------------------------------------------------------------------------

@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking_endpoint(
    data: BookingCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> BookingResponse:
    """
    Create a new booking.

    Supply one `attendees` entry per ticket purchased — each entry requires:
    - `first_name`, `last_name`
    - `email` + `confirm_email` (must match)
    - `phone`
    """
    order = create_booking(
        session,
        current_user,
        event_id=data.event_id,
        ticket_type_id=data.ticket_type_id,
        quantity=data.quantity,
        attendees=data.attendees,
    )
    logger.info(
        "User %s booked event %s — order %s (%d ticket(s))",
        current_user.uuid,
        data.event_id,
        order.uuid,
        data.quantity,
    )
    return BookingResponse.from_order(order)


# ---------------------------------------------------------------------------
# List / get bookings
# ---------------------------------------------------------------------------

@router.get("/me", response_model=list[BookingResponse])
def list_my_bookings(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[BookingResponse]:
    return [BookingResponse.from_order(o) for o in list_user_bookings(session, current_user)]


@router.get("/{order_id}", response_model=BookingResponse)
def get_booking_endpoint(
    order_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> BookingResponse:
    order = get_booking(session, current_user, order_id)
    return BookingResponse.from_order(order)


# ---------------------------------------------------------------------------
# Attendee details
# ---------------------------------------------------------------------------

@router.get("/{order_id}/attendees", response_model=list[AttendeeDetailResponse])
def get_attendees_endpoint(
    order_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[AttendeeDetailResponse]:
    """Retrieve the attendee details captured for each ticket in this order."""
    attendees = get_booking_attendees(session, current_user, order_id)
    return [AttendeeDetailResponse.model_validate(a) for a in attendees]


# ---------------------------------------------------------------------------
# Payment — Paystack
# ---------------------------------------------------------------------------

@router.post("/{order_id}/pay/paystack", response_model=PaystackInitResponse)
def paystack_init_endpoint(
    order_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> PaystackInitResponse:
    """
    Initialize a Paystack payment for the booking.

    Returns an `authorization_url` — redirect the user there to complete payment.
    After payment, Paystack will POST to `/bookings/paystack/webhook` to confirm.
    """
    result = initialize_paystack_payment(session, current_user, order_id)
    logger.info("Paystack payment initialized for order %s (ref: %s)", order_id, result["reference"])
    return PaystackInitResponse(**result)


@router.post(
    "/paystack/webhook",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,  # hide from public docs
)
async def paystack_webhook_endpoint(
    request: Request,
    session: Session = Depends(get_session),
    x_paystack_signature: str = Header(..., alias="x-paystack-signature"),
):
    """
    Paystack webhook — verifies HMAC signature and fulfills the order on
    `charge.success` events. Must be reachable by Paystack's servers.
    """
    payload = await request.body()
    verify_paystack_webhook(session, payload, x_paystack_signature)
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Payment — manual (legacy / testing)
# ---------------------------------------------------------------------------

@router.post("/{order_id}/pay", response_model=PaymentResponse)
def pay_booking_endpoint(
    order_id: UUID,
    data: PaymentRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> PaymentResponse:
    order = pay_booking(session, current_user, order_id, **data.model_dump())
    logger.info("User %s paid for booking %s (manual)", current_user.uuid, order_id)
    return PaymentResponse.model_validate(order.payment)


# ---------------------------------------------------------------------------
# Cancel booking
# ---------------------------------------------------------------------------

@router.post("/{order_id}/cancel", response_model=BookingResponse)
def cancel_booking_endpoint(
    order_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> BookingResponse:
    order = cancel_booking(session, current_user, order_id)
    logger.info("User %s cancelled booking %s", current_user.uuid, order_id)
    return BookingResponse.from_order(order)
