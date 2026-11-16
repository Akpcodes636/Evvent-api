import re
from datetime import datetime, timedelta
from uuid import UUID

import httpx
from sqlmodel import Session, select, func

from core.config import settings
from core.exceptions import AppError
from event.schema import (
    CheckinAttendee,
    EventAttendeeItem,
    EventCreate,
    EventUpdate,
    OrganizerOrderItem,
    TicketTypeUpdate,
)
from model.booking import AttendeeDetail, Order, OrderStatus
from model.event import (
    Category,
    Event,
    EventCategoryLink,
    EventStatus,
    TicketType,
    UserCategoryPreference,
)
from model.user import AccountType, User



def ensure_event_access(
    event: Event,
    user: User,
) -> None:
    """
    Ensure the user is allowed to manage the event.

    Admins can manage any event.

    Individual and organization accounts can manage
    events they own.
    """
    if user.account_type == AccountType.admin:
        return

    if (
        user.account_type in (
            AccountType.individual,
            AccountType.organization,
        )
        and event.organizer_id == user.uuid
    ):
        return

    raise AppError(
        "You do not have permission to manage this event",
        status_code=403,
    )


# ============================================================
# CATEGORIES
# ============================================================


def create_category(
    session: Session,
    *,
    name: str,
) -> Category:
    existing = session.exec(
        select(Category).where(
            Category.name == name
        )
    ).first()

    if existing:
        return existing

    category = Category(name=name)

    session.add(category)
    session.commit()
    session.refresh(category)

    return category


def list_categories(
    session: Session,
) -> list[Category]:
    return list(
        session.exec(
            select(Category).order_by(Category.name)
        ).all()
    )


def _get_categories(
    session: Session,
    category_ids: list[UUID],
) -> list[Category]:
    if not category_ids:
        return []

    categories = session.exec(
        select(Category).where(
            Category.uuid.in_(category_ids)
        )
    ).all()

    if len(categories) != len(set(category_ids)):
        raise AppError(
            "One or more categories were not found",
            status_code=404,
        )

    return list(categories)


# ============================================================
# USER CATEGORY PREFERENCES
# ============================================================


def get_user_category_preferences(
    session: Session,
    user: User,
) -> list[Category]:
    query = (
        select(Category)
        .join(
            UserCategoryPreference,
            UserCategoryPreference.category_id
            == Category.uuid,
        )
        .where(
            UserCategoryPreference.user_id == user.uuid
        )
        .order_by(Category.name)
    )

    return list(
        session.exec(query).all()
    )


def set_user_category_preferences(
    session: Session,
    user: User,
    category_ids: list[UUID],
) -> list[Category]:
    categories = _get_categories(
        session,
        category_ids,
    )

    existing_preferences = session.exec(
        select(UserCategoryPreference).where(
            UserCategoryPreference.user_id
            == user.uuid
        )
    ).all()

    for preference in existing_preferences:
        session.delete(preference)

    for category in categories:
        session.add(
            UserCategoryPreference(
                user_id=user.uuid,
                category_id=category.uuid,
            )
        )

    session.commit()

    return categories


# ============================================================
# EVENTS FOR USER
# ============================================================


# ============================================================
# RECOMMENDATIONS
# ============================================================

# Scoring weights for recommend_events_for_user.
_W_CATEGORY_PURCHASED = 3   # per purchase in a matching category
_W_CATEGORY_PREFERRED = 2   # per explicitly preferred matching category
_W_SAME_ORGANIZER = 4       # user bought from this organizer before
_W_SAME_LOCATION = 2        # user attended events in this location before
_W_FEATURED = 1


def recommend_events_for_user(
    session: Session,
    user: User,
    *,
    limit: int = 20,
) -> list[Event]:
    """
    Recommend upcoming events based on the user's purchase history.

    Signals come from the user's completed orders (categories, organizers and
    locations of events they bought tickets for) plus their explicit category
    preferences.

    Excluded automatically:
      - events that have already started (event_date <= now)
      - events that are not published (drafts, completed, cancelled)
      - events the user already holds a pending or completed order for
      - sold-out events
      - the user's own events
    """
    now = datetime.utcnow()

    purchased_event_ids = set(
        session.exec(
            select(Order.event_id)
            .where(Order.user_id == user.uuid)
            .where(Order.status.in_([OrderStatus.completed, OrderStatus.pending]))
            .distinct()
        ).all()
    )

    # --- Build the user's taste profile from completed purchases ----------
    history = session.exec(
        select(Event)
        .join(Order, Order.event_id == Event.uuid)
        .where(Order.user_id == user.uuid)
        .where(Order.status == OrderStatus.completed)
    ).all()

    category_counts: dict[UUID, int] = {}
    organizer_ids: set[UUID] = set()
    locations: set[str] = set()
    for past_event in history:
        organizer_ids.add(past_event.organizer_id)
        locations.add(past_event.location.strip().lower())
        for category in past_event.categories:
            category_counts[category.uuid] = category_counts.get(category.uuid, 0) + 1

    preferred_ids = {c.uuid for c in get_user_category_preferences(session, user)}

    # --- Candidate pool: upcoming, published, not already bought ----------
    query = (
        select(Event)
        .where(Event.status == EventStatus.published)
        .where(Event.event_date > now)
        .where(Event.organizer_id != user.uuid)
    )
    if purchased_event_ids:
        query = query.where(Event.uuid.not_in(purchased_event_ids))

    candidates = [
        event
        for event in session.exec(query).all()
        if any(t.total_quantity > t.sold_quantity for t in event.ticket_types)
    ]

    def score(event: Event) -> int:
        total = 0
        for category in event.categories:
            total += _W_CATEGORY_PURCHASED * category_counts.get(category.uuid, 0)
            if category.uuid in preferred_ids:
                total += _W_CATEGORY_PREFERRED
        if event.organizer_id in organizer_ids:
            total += _W_SAME_ORGANIZER
        if event.location.strip().lower() in locations:
            total += _W_SAME_LOCATION
        if event.featured:
            total += _W_FEATURED
        return total

    # Highest score first, soonest event breaks ties. Users with no history
    # all score 0/1, so they get featured-then-soonest upcoming events.
    candidates.sort(key=lambda e: (-score(e), e.event_date))

    return candidates[:limit]


# ============================================================
# AUTO-COMPLETE PAST EVENTS
# ============================================================

_DURATION_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(hours?|hrs?|h|minutes?|mins?|m|days?|d)",
    re.IGNORECASE,
)

# Used when an event's free-text duration can't be parsed.
_FALLBACK_DURATION = timedelta(hours=24)


def parse_duration(duration: str) -> timedelta | None:
    """Parse durations such as '4 hours', '30 mins', '2 days', '1h 30m'."""
    matches = list(_DURATION_PATTERN.finditer(duration or ""))
    leftover = re.sub(r"[\s,&]|and", "", _DURATION_PATTERN.sub("", duration or ""))
    if not matches or leftover:
        return None

    total = timedelta()
    for match in matches:
        amount = float(match.group(1))
        unit = match.group(2).lower()
        if unit.startswith("d"):
            total += timedelta(days=amount)
        elif unit.startswith("h"):
            total += timedelta(hours=amount)
        else:
            total += timedelta(minutes=amount)

    return total if total > timedelta() else None


def complete_past_events(session: Session) -> int:
    """
    Mark published events whose end time has passed as completed.

    End time = event_date + parsed duration (falls back to 24h if the
    duration text can't be parsed). Returns the number of events updated.
    """
    now = datetime.utcnow()

    events = session.exec(
        select(Event)
        .where(Event.status == EventStatus.published)
        .where(Event.event_date <= now)
    ).all()

    updated = 0
    for event in events:
        duration = parse_duration(event.duration) or _FALLBACK_DURATION
        if event.event_date + duration <= now:
            event.status = EventStatus.completed
            session.add(event)
            updated += 1

    if updated:
        session.commit()

    return updated



# ============================================================
# CREATE EVENT
# ============================================================

def create_event(
    session: Session,
    *,
    host: User,
    data: EventCreate,
) -> Event:
    """
    Create an event owned by the specified host.

    Events are created as drafts by default.  The organizer must publish
    them explicitly via POST /events/{id}/publish, or they are published
    automatically when a feature fee payment is confirmed.

    If data.featured is True the caller is responsible for initiating the
    feature payment immediately after this function returns.
    """

    categories = _get_categories(
        session,
        data.category_ids,
    )

    event = Event(
        organizer_id=host.uuid,
        title=data.title,
        host_name=data.host_name,
        host_phone=data.host_phone,
        description=data.description,
        location=data.location,
        event_date=data.event_date,
        duration=data.duration,
        event_type=data.event_type,
        status=EventStatus.draft,
        featured=data.featured,
    )

    session.add(event)
    session.flush()

    # Create ticket types
    for ticket_type in data.ticket_types:
        session.add(
            TicketType(
                event_id=event.uuid,
                name=ticket_type.name,
                price=ticket_type.price,
                total_quantity=ticket_type.total_quantity,
            )
        )

    # Attach categories
    for category in categories:
        session.add(
            EventCategoryLink(
                event_id=event.uuid,
                category_id=category.uuid,
            )
        )

    session.commit()
    session.refresh(event)

    return event

# ============================================================
# GET EVENT
# ============================================================


def get_event(
    session: Session,
    event_id: UUID,
) -> Event:
    event = session.get(
        Event,
        event_id,
    )

    if not event:
        raise AppError(
            "Event not found",
            status_code=404,
        )

    return event


# ============================================================
# LIST EVENTS
# ============================================================


def list_events(
    session: Session,
    *,
    location: str | None = None,
    category_id: UUID | None = None,
    search: str | None = None,
    event_type: str | None = None,
    status: EventStatus | None = None,
    featured: bool | None = None,
    host_id: UUID | None = None,
) -> list[Event]:

    query = select(Event)

    if location:
        query = query.where(
            Event.location.ilike(
                f"%{location}%"
            )
        )

    if search:
        query = query.where(
            Event.title.ilike(
                f"%{search}%"
            )
        )

    if event_type:
        query = query.where(
            Event.event_type == event_type
        )

    if status:
        query = query.where(
            Event.status == status
        )

    if featured is not None:
        query = query.where(
            Event.featured == featured
        )

    if host_id:
        query = query.where(
            Event.organizer_id == host_id
        )

    if category_id:
        query = (
            query
            .join(
                EventCategoryLink,
                EventCategoryLink.event_id
                == Event.uuid,
            )
            .where(
                EventCategoryLink.category_id
                == category_id
            )
        )

    query = query.order_by(
        Event.event_date
    )

    return list(
        session.exec(query).all()
    )

def list_events_paginated(
    session: Session,
    *,
    page_num: int = 1,
    page_size: int = 10,
    location: str | None = None,
    category_id: UUID | None = None,
    search: str | None = None,
    event_type: str | None = None,
    status: EventStatus | None = None,
    featured: bool | None = None,
) -> tuple[list[Event], int]:
    query = select(Event)

    if location:
        query = query.where(
            Event.location.ilike(f"%{location}%")
        )

    if search:
        query = query.where(
            Event.title.ilike(f"%{search}%")
        )

    if event_type:
        query = query.where(Event.event_type == event_type)

    if status is not None:
        query = query.where(Event.status == status)

    if featured is not None:
        query = query.where(Event.featured == featured)

    if category_id:
        query = (
            query
            .join(
                EventCategoryLink,
                EventCategoryLink.event_id == Event.uuid,
            )
            .where(EventCategoryLink.category_id == category_id)
        )

    # Count all matching events before applying pagination.
    count_query = (
        select(func.count())
        .select_from(query.order_by(None).subquery())
    )
    total = session.exec(count_query).one()

    # Retrieve only the requested page from the database.
    offset = (page_num - 1) * page_size

    paginated_query = (
        query
        .order_by(Event.event_date, Event.uuid)
        .offset(offset)
        .limit(page_size)
    )

    events = list(session.exec(paginated_query).all())

    return events, total

# ============================================================
# UPDATE EVENT
# ============================================================


def update_event(
    session: Session,
    event: Event,
    data: EventUpdate,
) -> Event:
    updates = data.model_dump(
        exclude_unset=True,
        exclude={"category_ids"},
    )

    for field, value in updates.items():
        setattr(
            event,
            field,
            value,
        )

    # Update categories if supplied
    if data.category_ids is not None:
        existing_links = session.exec(
            select(EventCategoryLink).where(
                EventCategoryLink.event_id
                == event.uuid
            )
        ).all()

        for link in existing_links:
            session.delete(link)

        categories = _get_categories(
            session,
            data.category_ids,
        )

        for category in categories:
            session.add(
                EventCategoryLink(
                    event_id=event.uuid,
                    category_id=category.uuid,
                )
            )

    session.add(event)
    session.commit()
    session.refresh(event)

    return event


# ============================================================
# DELETE EVENT
# ============================================================


def delete_event(
    session: Session,
    event: Event,
) -> None:
    # Delete category links
    category_links = session.exec(
        select(EventCategoryLink).where(
            EventCategoryLink.event_id
            == event.uuid
        )
    ).all()

    for link in category_links:
        session.delete(link)

    # Delete ticket types
    ticket_types = session.exec(
        select(TicketType).where(
            TicketType.event_id
            == event.uuid
        )
    ).all()

    for ticket_type in ticket_types:
        session.delete(ticket_type)

    # Event.image_url is just a URL stored on the event.
    # There is no EventImage database record to delete.

    session.delete(event)
    session.commit()


# ============================================================
# FEATURE EVENT
# ============================================================


def feature_event(
    session: Session,
    event: Event,
    *,
    featured: bool,
) -> Event:
    event.featured = featured

    session.add(event)
    session.commit()
    session.refresh(event)

    return event


# ============================================================
# FEATURE PAYMENT
# ============================================================


def initialize_feature_payment(
    session: Session,
    event: Event,
    user: User,
) -> dict:
    """
    Initiate a Paystack payment so the organizer can pay the feature fee.

    On success the authorization_url is returned for the frontend to redirect
    the user.  The Paystack reference is stored on the event so the webhook
    can identify it later.

    The event is published and marked as featured automatically when Paystack
    calls the webhook confirming the payment.
    """
    if not settings.PAYSTACK_SECRET_KEY:
        raise AppError(
            "Payment service is not configured. Please contact support.",
            status_code=503,
        )

    if event.organizer_id != user.uuid:
        if user.account_type != AccountType.admin:
            raise AppError(
                "You do not have permission to feature this event",
                status_code=403,
            )

    reference = f"EVVENT-FEAT-{event.uuid}"

    payload = {
        "email": user.email,
        "amount": settings.FEATURE_FEE,
        "reference": reference,
        "metadata": {
            "event_id": str(event.uuid),
            "type": "feature_fee",
            "organizer_id": str(user.uuid),
        },
        "callback_url": f"{settings.FRONTEND_BASE_URL}/payment/callback",
    }

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                "https://api.paystack.co/transaction/initialize",
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
                    "Content-Type": "application/json",
                },
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

    # Persist the reference so the webhook can match it to this event
    event.feature_paystack_reference = data["data"]["reference"]
    session.add(event)
    session.commit()

    return {
        "event_id": event.uuid,
        "authorization_url": data["data"]["authorization_url"],
        "reference": data["data"]["reference"],
        "amount": settings.FEATURE_FEE,
    }


# ============================================================
# PUBLISH EVENT
# ============================================================


def publish_event(
    session: Session,
    event: Event,
) -> Event:
    if event.status == EventStatus.published:
        return event

    event.status = EventStatus.published

    session.add(event)
    session.commit()
    session.refresh(event)

    return event


# ============================================================
# TICKET TYPES
# ============================================================


def get_ticket_type(
    session: Session,
    event: Event,
    ticket_type_id: UUID,
) -> TicketType:
    ticket_type = session.get(
        TicketType,
        ticket_type_id,
    )

    if (
        not ticket_type
        or ticket_type.event_id != event.uuid
    ):
        raise AppError(
            "Ticket type not found",
            status_code=404,
        )

    return ticket_type


def update_ticket_type(
    session: Session,
    ticket_type: TicketType,
    data: TicketTypeUpdate,
) -> TicketType:
    updates = data.model_dump(
        exclude_unset=True
    )

    if (
        "total_quantity" in updates
        and updates["total_quantity"]
        < ticket_type.sold_quantity
    ):
        raise AppError(
            "Total quantity cannot be less than tickets already sold",
            status_code=400,
        )

    for field, value in updates.items():
        setattr(
            ticket_type,
            field,
            value,
        )

    session.add(ticket_type)
    session.commit()
    session.refresh(ticket_type)

    return ticket_type


# ============================================================
# ORGANIZER ORDERS
# ============================================================


def list_event_orders(
    session: Session,
    event: Event,
    *,
    status: OrderStatus | None = None,
) -> list[Order]:
    """Return all orders for a specific event, optionally filtered by status."""
    query = select(Order).where(Order.event_id == event.uuid)

    if status is not None:
        query = query.where(Order.status == status)

    query = query.order_by(Order.created_at.desc())

    return list(session.exec(query).all())


# ============================================================
# CHECK-IN
# ============================================================


def list_event_attendees(
    session: Session,
    actor: User,
    event_id: UUID,
) -> list[EventAttendeeItem]:
    """
    Return all completed orders for an event, each enriched with attendee
    details and check-in status.  Only the event organizer or an admin may
    call this.
    """
    event = get_event(session, event_id)
    ensure_event_access(event, actor)

    orders = list(
        session.exec(
            select(Order)
            .where(Order.event_id == event_id)
            .where(Order.status == OrderStatus.completed)
            .order_by(Order.created_at.desc())
        ).all()
    )

    rows: list[EventAttendeeItem] = []
    for order in orders:
        attendees = list(
            session.exec(
                select(AttendeeDetail)
                .where(AttendeeDetail.order_id == order.uuid)
                .order_by(AttendeeDetail.ticket_index)
            ).all()
        )

        buyer = order.user
        rows.append(
            EventAttendeeItem(
                order_id=order.uuid,
                order_ref=str(order.uuid).upper()[:8],
                buyer_name=f"{buyer.first_name} {buyer.last_name}".strip(),
                buyer_email=buyer.email,
                ticket_type=order.ticket_type.name,
                quantity=order.quantity,
                total_amount=order.total_amount,
                status=order.status,
                checked_in=order.checked_in,
                checked_in_at=order.checked_in_at,
                booked_at=order.created_at,
                attendees=[
                    CheckinAttendee(
                        uuid=a.uuid,
                        ticket_index=a.ticket_index,
                        full_name=a.full_name,
                        email=a.email,
                        phone=a.phone,
                    )
                    for a in attendees
                ],
            )
        )

    return rows


def checkin_order(
    session: Session,
    actor: User,
    event_id: UUID,
    order_id: UUID,
) -> Order:
    """
    Mark an order as checked in.  The QR code encodes the order UUID so
    scanning it gives you the order_id directly.

    Only the event organizer or an admin may check attendees in.
    Raises 404 if the order doesn't belong to this event, 400 if it's not
    a completed order, and 409 if it's already been checked in.
    """
    event = get_event(session, event_id)
    ensure_event_access(event, actor)

    order = session.get(Order, order_id)
    if not order or order.event_id != event_id:
        raise AppError("Booking not found for this event", status_code=404)

    if order.status != OrderStatus.completed:
        raise AppError(
            f"Cannot check in a booking with status '{order.status.value}'",
            status_code=400,
        )

    if order.checked_in:
        raise AppError("This ticket has already been checked in", status_code=409)

    order.checked_in = True
    order.checked_in_at = datetime.utcnow()
    order.updated_at = datetime.utcnow()
    session.add(order)
    session.commit()
    session.refresh(order)
    return order