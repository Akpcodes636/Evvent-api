import hashlib
import hmac
import uuid as _uuid
from datetime import datetime

import httpx
from sqlmodel import Session, select

from booking.schema import AttendeeDetailCreate, CartAttendee, CartItemCreate, CartItemUpdate
from core.config import settings
from core.exceptions import AppError
from model.booking import AttendeeDetail, Cart, Order, OrderStatus, Payment, PaymentStatus
from model.event import Event, EventStatus, TicketType
from model.user import AccountType, User
from worker.tasks import task_send_booking_confirmation


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_event_and_ticket_type(
    session: Session, event_id: _uuid.UUID, ticket_type_id: _uuid.UUID
) -> tuple[Event, TicketType]:
    event = session.get(Event, event_id)
    if not event or event.status != EventStatus.published:
        raise AppError("Event not found or not available", status_code=404)

    ticket_type = session.get(TicketType, ticket_type_id)
    if not ticket_type or ticket_type.event_id != event.uuid:
        raise AppError("Ticket type not found for this event", status_code=404)

    return event, ticket_type



def _split_full_name(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().split(maxsplit=1)

    if not parts:
        raise ValueError("Attendee full name cannot be empty")

    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ""

    return first_name, last_name



def _save_attendees(
    session: Session,
    order: Order,
    attendees: list[AttendeeDetailCreate],
) -> None:
    for i, attendee in enumerate(attendees, start=1):
        first_name, last_name = _split_full_name(attendee.full_name)

        session.add(
            AttendeeDetail(
                order_id=order.uuid,
                ticket_index=i,
                first_name=first_name,
                last_name=last_name,
                email=str(attendee.email),
                phone=attendee.phone,
            )
        )


# ---------------------------------------------------------------------------
# Booking CRUD
# ---------------------------------------------------------------------------

def create_booking(
    session: Session,
    user: User,
    *,
    event_id: _uuid.UUID,
    ticket_type_id: _uuid.UUID,
    quantity: int,
    attendees: list[AttendeeDetailCreate],
) -> Order:
    event, ticket_type = _get_event_and_ticket_type(session, event_id, ticket_type_id)

    available = ticket_type.total_quantity - ticket_type.sold_quantity
    if quantity > available:
        raise AppError(
            f"Only {available} ticket(s) available for '{ticket_type.name}'",
            status_code=400,
        )

    is_free = event.event_type.value == "free"
    order = Order(
        user_id=user.uuid,
        event_id=event.uuid,
        ticket_type_id=ticket_type.uuid,
        quantity=quantity,
        total_amount=0 if is_free else ticket_type.price * quantity,
        is_free=is_free,
        status=OrderStatus.completed if is_free else OrderStatus.pending,
    )
    session.add(order)
    session.flush()  # populate order.uuid before saving attendees

    _save_attendees(session, order, attendees)

    if is_free:
        ticket_type.sold_quantity += quantity
        session.add(ticket_type)

    session.commit()
    session.refresh(order)

    if is_free:
        session.add(
            Payment(
                order_id=order.uuid,
                amount=0,
                status=PaymentStatus.completed,
                provider="free",
            )
        )
        session.commit()
        session.refresh(order)
        task_send_booking_confirmation.delay(str(order.uuid))

    return order


def list_user_bookings(session: Session, user: User) -> list[Order]:
    return list(
        session.exec(
            select(Order).where(Order.user_id == user.uuid).order_by(Order.created_at.desc())
        ).all()
    )


def get_booking(session: Session, user: User, order_id: _uuid.UUID) -> Order:
    order = session.get(Order, order_id)
    if not order:
        raise AppError("Booking not found", status_code=404)
    if user.account_type == AccountType.admin:
        return order
    if order.user_id != user.uuid and order.event.organizer_id != user.uuid:
        raise AppError("You do not have permission to view this booking", status_code=403)
    return order


def get_booking_attendees(
    session: Session, user: User, order_id: _uuid.UUID
) -> list[AttendeeDetail]:
    order = get_booking(session, user, order_id)
    return list(
        session.exec(
            select(AttendeeDetail)
            .where(AttendeeDetail.order_id == order.uuid)
            .order_by(AttendeeDetail.ticket_index)
        ).all()
    )


def cancel_booking(session: Session, user: User, order_id: _uuid.UUID) -> Order:
    order = get_booking(session, user, order_id)
    if order.status in (OrderStatus.cancelled, OrderStatus.refunded):
        raise AppError(f"Booking is already {order.status.value}", status_code=400)

    if order.status == OrderStatus.completed:
        order.ticket_type.sold_quantity = max(
            0, order.ticket_type.sold_quantity - order.quantity
        )
        session.add(order.ticket_type)
        order.status = OrderStatus.refunded
        if order.payment:
            order.payment.status = PaymentStatus.refunded
            session.add(order.payment)
    else:
        order.status = OrderStatus.cancelled

    order.updated_at = datetime.utcnow()
    session.add(order)
    session.commit()
    session.refresh(order)
    return order


# ---------------------------------------------------------------------------
# Manual payment (kept for backward compat / testing)
# ---------------------------------------------------------------------------

def pay_booking(
    session: Session,
    user: User,
    order_id: _uuid.UUID,
    *,
    provider: str,
    reference: str | None,
) -> Order:
    order = get_booking(session, user, order_id)
    if order.is_free:
        raise AppError("Free bookings do not require payment", status_code=400)
    if order.status != OrderStatus.pending:
        raise AppError(f"Booking is already {order.status.value}", status_code=400)

    ticket_type = order.ticket_type
    available = ticket_type.total_quantity - ticket_type.sold_quantity
    if order.quantity > available:
        raise AppError(
            f"Only {available} ticket(s) remain for '{ticket_type.name}'",
            status_code=400,
        )

    ticket_type.sold_quantity += order.quantity
    order.status = OrderStatus.completed
    order.updated_at = datetime.utcnow()
    session.add(ticket_type)
    session.add(order)
    session.add(
        Payment(
            order_id=order.uuid,
            amount=order.total_amount,
            status=PaymentStatus.completed,
            provider=provider,
            reference=reference,
        )
    )
    session.commit()
    session.refresh(order)
    task_send_booking_confirmation.delay(str(order.uuid))
    return order


# ---------------------------------------------------------------------------
# Paystack
# ---------------------------------------------------------------------------

def _paystack_headers() -> dict:
    if not settings.PAYSTACK_SECRET_KEY:
        raise AppError(
            "Payment service is not configured. Please contact support.",
            status_code=503,
        )
    return {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }


def initialize_paystack_payment(
    session: Session, user: User, order_id: _uuid.UUID
) -> dict:
    """
    Initialize a Paystack transaction for the given order.
    Returns the Paystack response data (authorization_url, access_code, reference).
    """
    order = get_booking(session, user, order_id)

    if order.is_free:
        raise AppError("Free bookings do not require payment", status_code=400)
    if order.status != OrderStatus.pending:
        raise AppError(
            f"Cannot pay for a booking that is already '{order.status.value}'",
            status_code=400,
        )

    # Determine the primary attendee (first ticket) for Paystack metadata
    primary_attendee = next(
        (a for a in session.exec(
            select(AttendeeDetail)
            .where(AttendeeDetail.order_id == order.uuid)
            .order_by(AttendeeDetail.ticket_index)
        ).all()),
        None,
    )

    email = primary_attendee.email if primary_attendee else user.email
    customer_name = (
    primary_attendee.full_name
    if primary_attendee
    else f"{user.first_name} {user.last_name}"
)

    payload = {
        "email": email,
        "amount": order.total_amount,  # already in kobo
        "reference": f"EVVENT-{order.uuid}",
        "metadata": {
            "order_id": str(order.uuid),
            "customer_name": customer_name,
            "event_id": str(order.event_id),
        },
        "callback_url": f"{settings.PAYSTACK_BASE_URL}/callback",
    }

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                "https://api.paystack.co/transaction/initialize",
                json=payload,
                headers=_paystack_headers(),
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        raise AppError(
            f"Payment initialization failed: {exc.response.text}",
            status_code=502,
        ) from exc
    except httpx.RequestError as exc:
        raise AppError(
            "Could not reach payment provider. Please try again.",
            status_code=503,
        ) from exc

    if not data.get("status"):
        raise AppError(
            data.get("message", "Payment initialization failed"),
            status_code=502,
        )

    reference = data["data"]["reference"]

    # Persist the reference so we can match the webhook later
    order.paystack_reference = reference
    order.updated_at = datetime.utcnow()
    session.add(order)
    session.commit()

    return {
        "order_id": order.uuid,
        "authorization_url": data["data"]["authorization_url"],
        "access_code": data["data"]["access_code"],
        "reference": reference,
        "amount": order.total_amount,
    }


def _handle_feature_payment(session: Session, reference: str) -> bool:
    """
    Check whether *reference* belongs to an event feature fee payment and, if
    so, publish the event and mark it as featured.

    Returns True if the reference was handled, False otherwise.
    """
    from model.event import Event, EventStatus

    event = session.exec(
        select(Event).where(Event.feature_paystack_reference == reference)
    ).first()

    if not event:
        return False

    # Idempotent: already processed
    if event.featured and event.status == EventStatus.published:
        return True

    event.featured = True
    event.status = EventStatus.published
    session.add(event)
    session.commit()
    return True


def verify_paystack_webhook(session: Session, payload: bytes, signature: str) -> None:
    """
    Validate the Paystack webhook signature and fulfill the order on success.
    Raises AppError on invalid signature or unexpected event type.
    """
    if not settings.PAYSTACK_SECRET_KEY:
        raise AppError("Payment service is not configured", status_code=503)

    expected = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode("utf-8"),
        payload,
        hashlib.sha512,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        raise AppError("Invalid webhook signature", status_code=400)

    import json

    body = json.loads(payload)
    event_type = body.get("event", "")

    if event_type != "charge.success":
        # Acknowledge non-success events without processing
        return

    reference = body.get("data", {}).get("reference", "")

    # Feature fee payments use the "EVVENT-FEAT-" prefix — handle separately
    if _handle_feature_payment(session, reference):
        return

    order = session.exec(
        select(Order).where(Order.paystack_reference == reference)
    ).first()

    if not order:
        # Unknown reference — ignore silently (may belong to another service)
        return

    if order.status != OrderStatus.pending:
        # Already processed (duplicate webhook delivery)
        return

    ticket_type = order.ticket_type
    available = ticket_type.total_quantity - ticket_type.sold_quantity
    if order.quantity > available:
        # Edge case: tickets sold out between init and confirmation
        order.status = OrderStatus.cancelled
        session.add(order)
        session.commit()
        return

    ticket_type.sold_quantity += order.quantity
    order.status = OrderStatus.completed
    order.updated_at = datetime.utcnow()
    session.add(ticket_type)
    session.add(order)
    session.add(
        Payment(
            order_id=order.uuid,
            amount=order.total_amount,
            status=PaymentStatus.completed,
            provider="paystack",
            reference=reference,
        )
    )
    session.commit()
    task_send_booking_confirmation.delay(str(order.uuid))


# ---------------------------------------------------------------------------
# Cart (Booking Wishlist)
# ---------------------------------------------------------------------------

def add_to_cart(
    session: Session,
    user: User,
    *,
    event_id: _uuid.UUID,
    ticket_type_id: _uuid.UUID,
    quantity: int,
) -> Cart:
    """
    Add a ticket selection to the user's cart.

    If the user already has a cart item for the same event + ticket type,
    the quantity is updated. Otherwise a new cart item is created.
    """
    event, ticket_type = _get_event_and_ticket_type(session, event_id, ticket_type_id)

    available = ticket_type.total_quantity - ticket_type.sold_quantity
    if quantity > available:
        raise AppError(
            f"Only {available} ticket(s) available for '{ticket_type.name}'",
            status_code=400,
        )

    existing = session.exec(
        select(Cart).where(
            Cart.user_id == user.uuid,
            Cart.event_id == event.uuid,
            Cart.ticket_type_id == ticket_type.uuid,
        )
    ).first()

    if existing:
        existing.quantity = quantity
        existing.updated_at = datetime.utcnow()
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    cart_item = Cart(
        user_id=user.uuid,
        event_id=event.uuid,
        ticket_type_id=ticket_type.uuid,
        quantity=quantity,
    )
    session.add(cart_item)
    session.commit()
    session.refresh(cart_item)
    return cart_item


def list_cart(session: Session, user: User) -> list[Cart]:
    return list(
        session.exec(
            select(Cart)
            .where(Cart.user_id == user.uuid)
            .order_by(Cart.created_at.desc())
        ).all()
    )


def get_cart_item(session: Session, user: User, cart_item_id: _uuid.UUID) -> Cart:
    item = session.get(Cart, cart_item_id)
    if not item or item.user_id != user.uuid:
        raise AppError("Cart item not found", status_code=404)
    return item


def update_cart_item(
    session: Session,
    user: User,
    cart_item_id: _uuid.UUID,
    *,
    quantity: int | None = None,
    attendees: list | None = None,
) -> Cart:
    item = get_cart_item(session, user, cart_item_id)

    if quantity is not None:
        ticket_type = item.ticket_type
        available = ticket_type.total_quantity - ticket_type.sold_quantity
        if quantity > available:
            raise AppError(
                f"Only {available} ticket(s) available for '{ticket_type.name}'",
                status_code=400,
            )
        item.quantity = quantity

    if attendees is not None:
        # Cap to item.quantity (max 10 forms)
        capped = attendees[: item.quantity]
        item.attendees = [a.model_dump() for a in capped]

    item.updated_at = datetime.utcnow()
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def remove_from_cart(session: Session, user: User, cart_item_id: _uuid.UUID) -> None:
    item = get_cart_item(session, user, cart_item_id)
    session.delete(item)
    session.commit()


def checkout_cart_item(
    session: Session,
    user: User,
    cart_item_id: _uuid.UUID,
) -> Order:
    """
    Convert a cart item into a confirmed order.

    All attendee forms saved in the cart must be complete before checkout.
    On success the cart item is deleted.
    """
    item = get_cart_item(session, user, cart_item_id)

    saved = item.attendees or []
    if len(saved) != item.quantity:
        raise AppError(
            f"All {item.quantity} attendee form(s) must be filled before checkout. "
            f"Currently {len(saved)} saved.",
            status_code=400,
        )

    # Validate each saved attendee has all required fields
    attendee_objs: list[AttendeeDetailCreate] = []
    for idx, raw in enumerate(saved, start=1):
        missing = [f for f in ("full_name", "email", "phone") if not raw.get(f)]
        if missing:
            raise AppError(
                f"Attendee #{idx} is missing: {', '.join(missing)}",
                status_code=400,
            )
        # confirm_email defaults to email so the validator passes
        attendee_objs.append(
            AttendeeDetailCreate(
                full_name=raw["full_name"],
                email=raw["email"],
                confirm_email=raw["email"],
                phone=raw["phone"],
            )
        )

    order = create_booking(
        session,
        user,
        event_id=item.event_id,
        ticket_type_id=item.ticket_type_id,
        quantity=item.quantity,
        attendees=attendee_objs,
    )

    # Remove the cart item now that the order is created
    session.delete(item)
    session.commit()

    return order
