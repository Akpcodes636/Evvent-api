from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session

from admin.schema import (
    AdminEventListItem, DashboardStats, FinanceStats, OrderListItem, OrderStats,
    OrganizerListItem, OrganizerUpdate, PayoutCreate, PayoutListItem, PayoutStatusUpdate,
)
from admin.services import (
    create_payout, get_dashboard_stats, get_finance_stats, get_organizer, get_order_stats,
    list_orders, list_organizers, list_payouts, update_payout_status,
)
from auth.dependencies import require_roles
from auth.services import update_profile
from booking.services import cancel_booking, get_booking
from database.session import get_session
from event.services import list_events
from logger import logger
from model.event import EventStatus
from model.booking import OrderStatus
from model.user import User, UserRole

router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])

_dashboard_roles = require_roles(UserRole.admin, UserRole.organizer)
_admin_only = require_roles(UserRole.admin)


@router.get("/dashboard", response_model=DashboardStats)
def dashboard(
    session: Session = Depends(get_session),
    current_user: User = Depends(_dashboard_roles),
) -> DashboardStats:
    return get_dashboard_stats(session, current_user)


@router.get("/events", response_model=list[AdminEventListItem])
def manage_events(
    search: str | None = None,
    status: EventStatus | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(_dashboard_roles),
) -> list[AdminEventListItem]:
    organizer_id = None if current_user.role == UserRole.admin else current_user.uuid
    events = list_events(session, search=search, status=status, organizer_id=organizer_id)
    return [
        AdminEventListItem(
            uuid=e.uuid, title=e.title, date=e.event_date, status=e.status,
            tickets_sold=sum(t.sold_quantity for t in e.ticket_types), featured=e.featured,
        )
        for e in events
    ]


@router.get("/orders/stats", response_model=OrderStats)
def order_stats(
    session: Session = Depends(get_session),
    current_user: User = Depends(_dashboard_roles),
) -> OrderStats:
    return get_order_stats(session, current_user)


@router.get("/orders", response_model=list[OrderListItem])
def manage_orders(
    status: OrderStatus | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(_dashboard_roles),
) -> list[OrderListItem]:
    orders = list_orders(session, current_user, status=status)
    return [
        OrderListItem(
            order_id=o.uuid,
            event=o.event.title,
            buyer=f"{o.user.first_name} {o.user.last_name}",
            tickets=o.quantity,
            total=o.total_amount,
            type="free" if o.is_free else "paid",
            status=o.status,
            date=o.created_at,
        )
        for o in orders
    ]


@router.get("/orders/{order_id}", response_model=OrderListItem)
def get_order(
    order_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(_dashboard_roles),
) -> OrderListItem:
    o = get_booking(session, current_user, order_id)
    return OrderListItem(
        order_id=o.uuid, event=o.event.title, buyer=f"{o.user.first_name} {o.user.last_name}",
        tickets=o.quantity, total=o.total_amount, type="free" if o.is_free else "paid",
        status=o.status, date=o.created_at,
    )


@router.post("/orders/{order_id}/refund", response_model=OrderListItem)
def refund_order(
    order_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(_dashboard_roles),
) -> OrderListItem:
    o = cancel_booking(session, current_user, order_id)
    logger.info("User %s refunded order %s", current_user.uuid, order_id)
    return OrderListItem(
        order_id=o.uuid, event=o.event.title, buyer=f"{o.user.first_name} {o.user.last_name}",
        tickets=o.quantity, total=o.total_amount, type="free" if o.is_free else "paid",
        status=o.status, date=o.created_at,
    )


@router.get("/finance", response_model=FinanceStats)
def finance(
    session: Session = Depends(get_session),
    current_user: User = Depends(_dashboard_roles),
) -> FinanceStats:
    return get_finance_stats(session, current_user)


@router.get("/finance/payouts", response_model=list[PayoutListItem])
def payouts(
    session: Session = Depends(get_session),
    current_user: User = Depends(_dashboard_roles),
) -> list[PayoutListItem]:
    return [
        PayoutListItem(
            uuid=p.uuid, date=p.created_at, event=p.event.title if p.event else None,
            amount=p.amount, status=p.status,
        )
        for p in list_payouts(session, current_user)
    ]


@router.post("/finance/payouts", response_model=PayoutListItem)
def create_payout_endpoint(
    data: PayoutCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(_admin_only),
) -> PayoutListItem:
    payout = create_payout(session, **data.model_dump())
    logger.info("Admin %s created payout %s for organizer %s", current_user.uuid, payout.uuid, data.organizer_id)
    return PayoutListItem(
        uuid=payout.uuid, date=payout.created_at, event=payout.event.title if payout.event else None,
        amount=payout.amount, status=payout.status,
    )


@router.patch("/finance/payouts/{payout_id}", response_model=PayoutListItem)
def update_payout_status_endpoint(
    payout_id: UUID,
    data: PayoutStatusUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(_admin_only),
) -> PayoutListItem:
    payout = update_payout_status(session, payout_id, status=data.status)
    logger.info("Admin %s set payout %s status to %s", current_user.uuid, payout_id, data.status)
    return PayoutListItem(
        uuid=payout.uuid, date=payout.created_at, event=payout.event.title if payout.event else None,
        amount=payout.amount, status=payout.status,
    )


@router.get("/organizers", response_model=list[OrganizerListItem])
def get_organizers(
    session: Session = Depends(get_session),
    _: User = Depends(_admin_only),
) -> list[OrganizerListItem]:
    return [OrganizerListItem.model_validate(o) for o in list_organizers(session)]


@router.get("/organizers/{organizer_id}", response_model=OrganizerListItem)
def get_organizer_endpoint(
    organizer_id: UUID,
    session: Session = Depends(get_session),
    _: User = Depends(_admin_only),
) -> OrganizerListItem:
    return OrganizerListItem.model_validate(get_organizer(session, organizer_id))


@router.patch("/organizers/{organizer_id}", response_model=OrganizerListItem)
def update_organizer_endpoint(
    organizer_id: UUID,
    data: OrganizerUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(_admin_only),
) -> OrganizerListItem:
    organizer = get_organizer(session, organizer_id)
    organizer = update_profile(session, organizer, **data.model_dump())
    logger.info("Admin %s updated organizer %s", current_user.uuid, organizer_id)
    return OrganizerListItem.model_validate(organizer)
