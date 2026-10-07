from uuid import UUID

from sqlmodel import Session, select

from core.exceptions import AppError
from event.schema import (
    EventCreate,
    EventUpdate,
    TicketTypeUpdate,
)
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


def list_events_for_user(
    session: Session,
    user: User,
    *,
    status: EventStatus | None = EventStatus.published,
) -> list[Event]:
    category_ids = [
        category.uuid
        for category in get_user_category_preferences(
            session,
            user,
        )
    ]

    if not category_ids:
        return list_events(
            session,
            status=status,
        )

    query = (
        select(Event)
        .distinct()
        .join(
            EventCategoryLink,
            EventCategoryLink.event_id == Event.uuid,
        )
        .where(
            EventCategoryLink.category_id.in_(
                category_ids
            )
        )
    )

    if status:
        query = query.where(
            Event.status == status
        )

    query = query.order_by(
        Event.event_date
    )

    return list(
        session.exec(query).all()
    )


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

    Events are published immediately after creation.
    The event image is uploaded separately by the router
    to Cloudinary and stored in Event.image_url.
    """

    categories = _get_categories(
        session,
        data.category_ids,
    )

    event = Event(
        organizer_id=host.uuid,
        title=data.title,
        host_name=data.host_name,
        description=data.description,
        location=data.location,
        event_date=data.event_date,
        duration=data.duration,
        event_type=data.event_type,
        status=EventStatus.published,
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