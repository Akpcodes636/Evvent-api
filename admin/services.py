from datetime import datetime
from uuid import UUID

from sqlmodel import Session, func, select

from admin.schema import DashboardStats, FinanceStats, OrderStats
from core.exceptions import AppError
from model.booking import Order, OrderStatus, Payout, PayoutStatus
from model.event import Event, EventStatus, TicketType
from model.user import User, UserRole


def _scoped_event_ids(session: Session, user: User) -> list[UUID] | None:
    """None means unrestricted (platform admin); otherwise the organizer's own event ids."""
    if user.role == UserRole.admin:
        return None
    return list(session.exec(select(Event.uuid).where(Event.organizer_id == user.uuid)).all())


def _sum_orders(session: Session, event_ids: list[UUID] | None, status: OrderStatus) -> int:
    query = select(func.coalesce(func.sum(Order.total_amount), 0)).where(Order.status == status)
    if event_ids is not None:
        if not event_ids:
            return 0
        query = query.where(Order.event_id.in_(event_ids))
    return session.exec(query).one()


def get_dashboard_stats(session: Session, user: User) -> DashboardStats:
    event_ids = _scoped_event_ids(session, user)
    event_query = select(Event)
    if event_ids is not None:
        event_query = event_query.where(Event.organizer_id == user.uuid)
    events = session.exec(event_query).all()

    now = datetime.utcnow()
    active_events = sum(1 for e in events if e.status == EventStatus.published)
    upcoming_events = sum(1 for e in events if e.status == EventStatus.published and e.event_date > now)

    ids = [e.uuid for e in events]
    tickets_sold = 0
    if ids:
        tickets_sold = session.exec(
            select(func.coalesce(func.sum(TicketType.sold_quantity), 0)).where(TicketType.event_id.in_(ids))
        ).one()

    return DashboardStats(
        total_events=len(events),
        active_events=active_events,
        upcoming_events=upcoming_events,
        total_tickets_sold=tickets_sold,
        total_revenue=_sum_orders(session, ids, OrderStatus.completed),
    )


def get_order_stats(session: Session, user: User) -> OrderStats:
    event_ids = _scoped_event_ids(session, user)
    if event_ids is not None and not event_ids:
        return OrderStats(total_orders=0, pending_orders=0, completed_orders=0, refunded_orders=0, free_orders=0)

    query = select(Order)
    if event_ids is not None:
        query = query.where(Order.event_id.in_(event_ids))
    orders = session.exec(query).all()

    return OrderStats(
        total_orders=len(orders),
        pending_orders=sum(1 for o in orders if o.status == OrderStatus.pending),
        completed_orders=sum(1 for o in orders if o.status == OrderStatus.completed),
        refunded_orders=sum(1 for o in orders if o.status == OrderStatus.refunded),
        free_orders=sum(1 for o in orders if o.is_free),
    )


def list_orders(session: Session, user: User, *, status: OrderStatus | None = None) -> list[Order]:
    event_ids = _scoped_event_ids(session, user)
    if event_ids is not None and not event_ids:
        return []

    query = select(Order)
    if event_ids is not None:
        query = query.where(Order.event_id.in_(event_ids))
    if status:
        query = query.where(Order.status == status)
    query = query.order_by(Order.created_at.desc())
    return list(session.exec(query).all())


def get_finance_stats(session: Session, user: User) -> FinanceStats:
    event_ids = _scoped_event_ids(session, user)
    total_revenue = _sum_orders(session, event_ids, OrderStatus.completed)
    pending = _sum_orders(session, event_ids, OrderStatus.pending)

    payout_query = select(func.coalesce(func.sum(Payout.amount), 0)).where(Payout.status == PayoutStatus.paid)
    if user.role != UserRole.admin:
        payout_query = payout_query.where(Payout.organizer_id == user.uuid)
    paid_out = session.exec(payout_query).one()

    total_events = len(event_ids) if event_ids is not None else session.exec(
        select(func.count()).select_from(Event)
    ).one()

    return FinanceStats(
        total_revenue=total_revenue,
        available_balance=total_revenue - paid_out,
        pending=pending,
        total_events=total_events,
    )


def list_payouts(session: Session, user: User) -> list[Payout]:
    query = select(Payout)
    if user.role != UserRole.admin:
        query = query.where(Payout.organizer_id == user.uuid)
    query = query.order_by(Payout.created_at.desc())
    return list(session.exec(query).all())


def create_payout(session: Session, *, organizer_id: UUID, event_id: UUID | None, amount: int) -> Payout:
    organizer = session.get(User, organizer_id)
    if not organizer or organizer.role != UserRole.organizer:
        raise AppError("Organizer not found", status_code=404)
    if event_id and not session.get(Event, event_id):
        raise AppError("Event not found", status_code=404)

    payout = Payout(organizer_id=organizer_id, event_id=event_id, amount=amount)
    session.add(payout)
    session.commit()
    session.refresh(payout)
    return payout


def update_payout_status(session: Session, payout_id: UUID, *, status: PayoutStatus) -> Payout:
    payout = session.get(Payout, payout_id)
    if not payout:
        raise AppError("Payout not found", status_code=404)
    payout.status = status
    payout.updated_at = datetime.utcnow()
    session.add(payout)
    session.commit()
    session.refresh(payout)
    return payout


def list_organizers(session: Session) -> list[User]:
    return list(session.exec(select(User).where(User.role == UserRole.organizer)).all())


def get_organizer(session: Session, organizer_id: UUID) -> User:
    organizer = session.get(User, organizer_id)
    if not organizer or organizer.role != UserRole.organizer:
        raise AppError("Organizer not found", status_code=404)
    return organizer
