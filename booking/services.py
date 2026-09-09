from datetime import datetime
from uuid import UUID

from sqlmodel import Session, select

from core.exceptions import AppError
from model.booking import Order, OrderStatus, Payment, PaymentStatus
from model.event import Event, EventStatus, TicketType
from model.user import User, UserRole


def _get_event_and_ticket_type(session: Session, event_id: UUID, ticket_type_id: UUID) -> tuple[Event, TicketType]:
    event = session.get(Event, event_id)
    if not event or event.status != EventStatus.published:
        raise AppError("Event not found", status_code=404)

    ticket_type = session.get(TicketType, ticket_type_id)
    if not ticket_type or ticket_type.event_id != event.uuid:
        raise AppError("Ticket type not found", status_code=404)

    return event, ticket_type


def create_booking(session: Session, user: User, *, event_id: UUID, ticket_type_id: UUID, quantity: int) -> Order:
    event, ticket_type = _get_event_and_ticket_type(session, event_id, ticket_type_id)

    available = ticket_type.total_quantity - ticket_type.sold_quantity
    if quantity > available:
        raise AppError(f"Only {available} ticket(s) available for {ticket_type.name}", status_code=400)

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

    if is_free:
        ticket_type.sold_quantity += quantity
        session.add(ticket_type)

    session.commit()
    session.refresh(order)

    if is_free:
        session.add(Payment(order_id=order.uuid, amount=0, status=PaymentStatus.completed, provider="free"))
        session.commit()
        session.refresh(order)

    return order


def list_user_bookings(session: Session, user: User) -> list[Order]:
    return list(session.exec(select(Order).where(Order.user_id == user.uuid).order_by(Order.created_at.desc())).all())


def get_booking(session: Session, user: User, order_id: UUID) -> Order:
    order = session.get(Order, order_id)
    if not order:
        raise AppError("Booking not found", status_code=404)
    if user.role == UserRole.user and order.user_id != user.uuid:
        raise AppError("You do not have permission to view this booking", status_code=403)
    if user.role == UserRole.organizer and order.user_id != user.uuid and order.event.organizer_id != user.uuid:
        raise AppError("You do not have permission to view this booking", status_code=403)
    return order


def pay_booking(session: Session, user: User, order_id: UUID, *, provider: str, reference: str | None) -> Order:
    order = get_booking(session, user, order_id)
    if order.is_free:
        raise AppError("Free bookings do not require payment", status_code=400)
    if order.status != OrderStatus.pending:
        raise AppError(f"Booking is already {order.status.value}", status_code=400)

    ticket_type = order.ticket_type
    available = ticket_type.total_quantity - ticket_type.sold_quantity
    if order.quantity > available:
        raise AppError(f"Only {available} ticket(s) remain for {ticket_type.name}", status_code=400)

    ticket_type.sold_quantity += order.quantity
    order.status = OrderStatus.completed
    order.updated_at = datetime.utcnow()
    session.add(ticket_type)
    session.add(order)
    session.add(Payment(
        order_id=order.uuid, amount=order.total_amount,
        status=PaymentStatus.completed, provider=provider, reference=reference,
    ))
    session.commit()
    session.refresh(order)
    return order


def cancel_booking(session: Session, user: User, order_id: UUID) -> Order:
    order = get_booking(session, user, order_id)
    if order.status in (OrderStatus.cancelled, OrderStatus.refunded):
        raise AppError(f"Booking is already {order.status.value}", status_code=400)

    if order.status == OrderStatus.completed:
        order.ticket_type.sold_quantity = max(0, order.ticket_type.sold_quantity - order.quantity)
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
