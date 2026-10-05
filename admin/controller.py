
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session

from admin.schema import (
    AdminEventListItem,
    DashboardStats,
    FinanceStats,
    HostListItem,
    HostUpdate,
    OrderListItem,
    OrderStats,
    PayoutCreate,
    PayoutListItem,
    PayoutStatusUpdate,
)
from admin.services import (
    create_payout,
    get_dashboard_stats,
    get_finance_stats,
    get_host,
    get_order_stats,
    list_hosts,
    list_orders,
    list_payouts,
    update_payout_status,
)
from auth.dependencies import require_roles
from auth.services import update_profile
from booking.services import cancel_booking, get_booking
from database.session import get_session
from event.services import list_events
from logger import logger
from model.booking import OrderStatus
from model.event import EventStatus
from model.user import AccountType, User


router = APIRouter(
    prefix="/admin",
    tags=["Admin Dashboard"],
)

_dashboard_roles = require_roles(
    AccountType.admin,
    AccountType.individual,
    AccountType.organization,
)

_admin_only = require_roles(
    AccountType.admin,
)


@router.get(
    "/dashboard",
    response_model=DashboardStats,
)
def dashboard(
    session: Session = Depends(get_session),
    current_user: User = Depends(_dashboard_roles),
) -> DashboardStats:
    return get_dashboard_stats(
        session,
        current_user,
    )


@router.get(
    "/events",
    response_model=list[AdminEventListItem],
)
def manage_events(
    search: str | None = None,
    status: EventStatus | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(_dashboard_roles),
) -> list[AdminEventListItem]:

    host_id = (
        None
        if current_user.account_type == AccountType.admin
        else current_user.uuid
    )

    events = list_events(
        session,
        search=search,
        status=status,
        host_id=host_id,
    )

    return [
        AdminEventListItem(
            uuid=event.uuid,
            title=event.title,
            date=event.event_date,
            status=event.status,
            tickets_sold=sum(
                ticket.sold_quantity
                for ticket in event.ticket_types
            ),
            featured=event.featured,
        )
        for event in events
    ]


@router.get(
    "/orders/stats",
    response_model=OrderStats,
)
def order_stats(
    session: Session = Depends(get_session),
    current_user: User = Depends(_dashboard_roles),
) -> OrderStats:
    return get_order_stats(
        session,
        current_user,
    )


@router.get(
    "/orders",
    response_model=list[OrderListItem],
)
def manage_orders(
    status: OrderStatus | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(_dashboard_roles),
) -> list[OrderListItem]:

    orders = list_orders(
        session,
        current_user,
        status=status,
    )

    return [
        OrderListItem(
            order_id=order.uuid,
            event=order.event.title,
            buyer=(
                f"{order.user.first_name} "
                f"{order.user.last_name}"
            ),
            tickets=order.quantity,
            total=order.total_amount,
            type="free" if order.is_free else "paid",
            status=order.status,
            date=order.created_at,
        )
        for order in orders
    ]


@router.get(
    "/orders/{order_id}",
    response_model=OrderListItem,
)
def get_order(
    order_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(_dashboard_roles),
) -> OrderListItem:

    order = get_booking(
        session,
        current_user,
        order_id,
    )

    return OrderListItem(
        order_id=order.uuid,
        event=order.event.title,
        buyer=(
            f"{order.user.first_name} "
            f"{order.user.last_name}"
        ),
        tickets=order.quantity,
        total=order.total_amount,
        type="free" if order.is_free else "paid",
        status=order.status,
        date=order.created_at,
    )


@router.post(
    "/orders/{order_id}/refund",
    response_model=OrderListItem,
)
def refund_order(
    order_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(_dashboard_roles),
) -> OrderListItem:

    order = cancel_booking(
        session,
        current_user,
        order_id,
    )

    logger.info(
        "User %s refunded order %s",
        current_user.uuid,
        order_id,
    )

    return OrderListItem(
        order_id=order.uuid,
        event=order.event.title,
        buyer=(
            f"{order.user.first_name} "
            f"{order.user.last_name}"
        ),
        tickets=order.quantity,
        total=order.total_amount,
        type="free" if order.is_free else "paid",
        status=order.status,
        date=order.created_at,
    )


@router.get(
    "/finance",
    response_model=FinanceStats,
)
def finance(
    session: Session = Depends(get_session),
    current_user: User = Depends(_dashboard_roles),
) -> FinanceStats:
    return get_finance_stats(
        session,
        current_user,
    )


@router.get(
    "/finance/payouts",
    response_model=list[PayoutListItem],
)
def payouts(
    session: Session = Depends(get_session),
    current_user: User = Depends(_dashboard_roles),
) -> list[PayoutListItem]:

    return [
        PayoutListItem(
            uuid=payout.uuid,
            date=payout.created_at,
            event=(
                payout.event.title
                if payout.event
                else None
            ),
            amount=payout.amount,
            status=payout.status,
        )
        for payout in list_payouts(
            session,
            current_user,
        )
    ]


@router.post(
    "/finance/payouts",
    response_model=PayoutListItem,
)
def create_payout_endpoint(
    data: PayoutCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(_admin_only),
) -> PayoutListItem:

    payout = create_payout(
        session,
        **data.model_dump(),
    )

    logger.info(
        "Admin %s created payout %s for host %s",
        current_user.uuid,
        payout.uuid,
        data.host_id,
    )

    return PayoutListItem(
        uuid=payout.uuid,
        date=payout.created_at,
        event=(
            payout.event.title
            if payout.event
            else None
        ),
        amount=payout.amount,
        status=payout.status,
    )


@router.patch(
    "/finance/payouts/{payout_id}",
    response_model=PayoutListItem,
)
def update_payout_status_endpoint(
    payout_id: UUID,
    data: PayoutStatusUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(_admin_only),
) -> PayoutListItem:

    payout = update_payout_status(
        session,
        payout_id,
        status=data.status,
    )

    logger.info(
        "Admin %s set payout %s status to %s",
        current_user.uuid,
        payout_id,
        data.status,
    )

    return PayoutListItem(
        uuid=payout.uuid,
        date=payout.created_at,
        event=(
            payout.event.title
            if payout.event
            else None
        ),
        amount=payout.amount,
        status=payout.status,
    )


@router.get(
    "/hosts",
    response_model=list[HostListItem],
)
def get_hosts(
    session: Session = Depends(get_session),
    _: User = Depends(_admin_only),
) -> list[HostListItem]:

    return [
        HostListItem.model_validate(host)
        for host in list_hosts(session)
    ]


@router.get(
    "/hosts/{host_id}",
    response_model=HostListItem,
)
def get_host_endpoint(
    host_id: UUID,
    session: Session = Depends(get_session),
    _: User = Depends(_admin_only),
) -> HostListItem:

    return HostListItem.model_validate(
        get_host(
            session,
            host_id,
        )
    )


@router.patch(
    "/hosts/{host_id}",
    response_model=HostListItem,
)
def update_host_endpoint(
    host_id: UUID,
    data: HostUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(_admin_only),
) -> HostListItem:

    host = get_host(
        session,
        host_id,
    )

    host = update_profile(
        session,
        host,
        **data.model_dump(),
    )

    logger.info(
        "Admin %s updated host %s",
        current_user.uuid,
        host_id,
    )

    return HostListItem.model_validate(host)
