from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, status
from sqlmodel import Session

from auth.dependencies import get_current_user
from booking.schema import (
    AttendeeDetailResponse,
    BookingCreate,
    BookingResponse,
    CartItemCreate,
    CartItemResponse,
    CartItemUpdate,
    PaymentRequest,
    PaymentResponse,
    PaystackInitResponse,
)
from booking.services import (
    add_to_cart,
    cancel_booking,
    checkout_cart_item,
    create_booking,
    get_booking,
    get_booking_attendees,
    get_cart_item,
    initialize_paystack_payment,
    list_cart,
    list_user_bookings,
    pay_booking,
    remove_from_cart,
    update_cart_item,
    verify_paystack_webhook,
)
from database.session import get_session
from logger import logger
from model.user import User

router = APIRouter(prefix="/bookings", tags=["Bookings"])
cart_router = APIRouter(prefix="/cart", tags=["Cart"])


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
    - `full_name`,
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

# @router.get("/me", response_model=list[BookingResponse])
# def list_my_bookings(
#     session: Session = Depends(get_session),
#     current_user: User = Depends(get_current_user),
# ) -> list[BookingResponse]:
#     return [BookingResponse.from_order(o) for o in list_user_bookings(session, current_user)]


# @router.get("/{order_id}", response_model=BookingResponse)
# def get_booking_endpoint(
#     order_id: UUID,
#     session: Session = Depends(get_session),
#     current_user: User = Depends(get_current_user),
# ) -> BookingResponse:
#     order = get_booking(session, current_user, order_id)
#     return BookingResponse.from_order(order)


# # ---------------------------------------------------------------------------
# # Attendee details
# # ---------------------------------------------------------------------------

# @router.get("/{order_id}/attendees", response_model=list[AttendeeDetailResponse])
# def get_attendees_endpoint(
#     order_id: UUID,
#     session: Session = Depends(get_session),
#     current_user: User = Depends(get_current_user),
# ) -> list[AttendeeDetailResponse]:
#     """Retrieve the attendee details captured for each ticket in this order."""
#     attendees = get_booking_attendees(session, current_user, order_id)
#     return [
#     AttendeeDetailResponse(
#         uuid=a.uuid,
#         ticket_index=a.ticket_index,
#         full_name=a.full_name,
#         email=a.email,
#         phone=a.phone,
#     )
#     for a in attendees
# ]


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


# ---------------------------------------------------------------------------
# Cart endpoints
# ---------------------------------------------------------------------------

@cart_router.post("/", response_model=CartItemResponse, status_code=status.HTTP_201_CREATED)
def add_to_cart_endpoint(
    data: CartItemCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CartItemResponse:
    """
    Add an event ticket selection to the cart (wishlist).

    If the same event + ticket type is already in the cart, the quantity is updated.
    Returns the cart item with attendee form slots pre-populated.
    """
    item = add_to_cart(
        session,
        current_user,
        event_id=data.event_id,
        ticket_type_id=data.ticket_type_id,
        quantity=data.quantity,
    )
    logger.info("User %s added ticket type %s (qty %d) to cart", current_user.uuid, data.ticket_type_id, data.quantity)
    return CartItemResponse.from_cart(item)


@cart_router.get("/", response_model=list[CartItemResponse])
def list_cart_endpoint(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[CartItemResponse]:
    """Return all cart items for the current user."""
    return [CartItemResponse.from_cart(item) for item in list_cart(session, current_user)]


@cart_router.get("/{cart_item_id}", response_model=CartItemResponse)
def get_cart_item_endpoint(
    cart_item_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CartItemResponse:
    item = get_cart_item(session, current_user, cart_item_id)
    return CartItemResponse.from_cart(item)


@cart_router.patch("/{cart_item_id}", response_model=CartItemResponse)
def update_cart_item_endpoint(
    cart_item_id: UUID,
    data: CartItemUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CartItemResponse:
    """
    Update quantity and/or save attendee form progress.

    Attendee list is capped at `quantity` (max 10).
    Submit partial attendee data to save progress — checkout validates completeness.
    """
    item = update_cart_item(
        session,
        current_user,
        cart_item_id,
        quantity=data.quantity,
        attendees=data.attendees,
    )
    return CartItemResponse.from_cart(item)


@cart_router.delete("/{cart_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_cart_endpoint(
    cart_item_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Remove an item from the cart."""
    remove_from_cart(session, current_user, cart_item_id)
    logger.info("User %s removed cart item %s", current_user.uuid, cart_item_id)


@cart_router.post("/{cart_item_id}/checkout", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def checkout_cart_item_endpoint(
    cart_item_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> BookingResponse:
    """
    Convert a cart item into a booking order.

    All attendee forms must be complete (full_name, email, phone for each ticket).
    The cart item is deleted after a successful checkout.
    """
    order = checkout_cart_item(session, current_user, cart_item_id)
    logger.info("User %s checked out cart item %s → order %s", current_user.uuid, cart_item_id, order.uuid)
    return BookingResponse.from_order(order)
