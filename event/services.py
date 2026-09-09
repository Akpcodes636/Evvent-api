from uuid import UUID

from sqlmodel import Session, select

from core.exceptions import AppError
from event.schema import EventCreate, EventUpdate, TicketTypeUpdate
from model.event import Category, Event, EventCategoryLink, EventImage, EventStatus, TicketType
from model.user import User, UserRole


def ensure_event_access(event: Event, user: User) -> None:
    """Only the organizer who owns the event, or a platform admin, may manage it."""
    if user.role == UserRole.admin:
        return
    if event.organizer_id != user.uuid:
        raise AppError("You do not have permission to manage this event", status_code=403)


def create_category(session: Session, *, name: str) -> Category:
    existing = session.exec(select(Category).where(Category.name == name)).first()
    if existing:
        return existing
    category = Category(name=name)
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


def list_categories(session: Session) -> list[Category]:
    return list(session.exec(select(Category).order_by(Category.name)).all())


def _get_categories(session: Session, category_ids: list[UUID]) -> list[Category]:
    if not category_ids:
        return []
    categories = session.exec(select(Category).where(Category.uuid.in_(category_ids))).all()
    if len(categories) != len(set(category_ids)):
        raise AppError("One or more categories were not found", status_code=404)
    return list(categories)


def create_event(session: Session, *, organizer: User, data: EventCreate) -> Event:
    categories = _get_categories(session, data.category_ids)

    event = Event(
        organizer_id=organizer.uuid,
        title=data.title,
        host_name=data.host_name,
        description=data.description,
        location=data.location,
        event_date=data.event_date,
        duration=data.duration,
        event_type=data.event_type,
        video_url=data.video_url,
    )
    session.add(event)
    session.flush()

    for ticket_type in data.ticket_types:
        session.add(TicketType(
            event_id=event.uuid,
            name=ticket_type.name,
            price=ticket_type.price,
            total_quantity=ticket_type.total_quantity,
        ))

    for category in categories:
        session.add(EventCategoryLink(event_id=event.uuid, category_id=category.uuid))

    session.commit()
    session.refresh(event)
    return event


def get_event(session: Session, event_id: UUID) -> Event:
    event = session.get(Event, event_id)
    if not event:
        raise AppError("Event not found", status_code=404)
    return event


def list_events(
    session: Session,
    *,
    location: str | None = None,
    category_id: UUID | None = None,
    search: str | None = None,
    event_type: str | None = None,
    status: EventStatus | None = None,
    featured: bool | None = None,
    organizer_id: UUID | None = None,
) -> list[Event]:
    query = select(Event)

    if location:
        query = query.where(Event.location.ilike(f"%{location}%"))
    if search:
        query = query.where(Event.title.ilike(f"%{search}%"))
    if event_type:
        query = query.where(Event.event_type == event_type)
    if status:
        query = query.where(Event.status == status)
    if featured is not None:
        query = query.where(Event.featured == featured)
    if organizer_id:
        query = query.where(Event.organizer_id == organizer_id)
    if category_id:
        query = query.join(EventCategoryLink, EventCategoryLink.event_id == Event.uuid).where(
            EventCategoryLink.category_id == category_id
        )

    query = query.order_by(Event.event_date)
    return list(session.exec(query).all())


def update_event(session: Session, event: Event, data: EventUpdate) -> Event:
    updates = data.model_dump(exclude_unset=True, exclude={"category_ids"})
    for field, value in updates.items():
        setattr(event, field, value)

    if data.category_ids is not None:
        session.exec(select(EventCategoryLink).where(EventCategoryLink.event_id == event.uuid)).all()
        for link in session.exec(select(EventCategoryLink).where(EventCategoryLink.event_id == event.uuid)).all():
            session.delete(link)
        for category in _get_categories(session, data.category_ids):
            session.add(EventCategoryLink(event_id=event.uuid, category_id=category.uuid))

    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def delete_event(session: Session, event: Event) -> None:
    for link in session.exec(select(EventCategoryLink).where(EventCategoryLink.event_id == event.uuid)).all():
        session.delete(link)
    for image in session.exec(select(EventImage).where(EventImage.event_id == event.uuid)).all():
        session.delete(image)
    for ticket_type in session.exec(select(TicketType).where(TicketType.event_id == event.uuid)).all():
        session.delete(ticket_type)
    session.delete(event)
    session.commit()


def feature_event(session: Session, event: Event, *, featured: bool) -> Event:
    event.featured = featured
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def add_event_images(session: Session, event: Event, urls: list[str]) -> list[EventImage]:
    has_primary = bool(session.exec(
        select(EventImage).where(EventImage.event_id == event.uuid, EventImage.is_primary == True)  # noqa: E712
    ).first())

    images = []
    for index, url in enumerate(urls):
        image = EventImage(event_id=event.uuid, url=url, is_primary=not has_primary and index == 0)
        session.add(image)
        images.append(image)

    session.commit()
    for image in images:
        session.refresh(image)
    return images


def delete_event_image(session: Session, event: Event, image_id: UUID) -> None:
    image = session.get(EventImage, image_id)
    if not image or image.event_id != event.uuid:
        raise AppError("Image not found", status_code=404)
    session.delete(image)
    session.commit()


def get_ticket_type(session: Session, event: Event, ticket_type_id: UUID) -> TicketType:
    ticket_type = session.get(TicketType, ticket_type_id)
    if not ticket_type or ticket_type.event_id != event.uuid:
        raise AppError("Ticket type not found", status_code=404)
    return ticket_type


def update_ticket_type(session: Session, ticket_type: TicketType, data: TicketTypeUpdate) -> TicketType:
    updates = data.model_dump(exclude_unset=True)
    if "total_quantity" in updates and updates["total_quantity"] < ticket_type.sold_quantity:
        raise AppError("Total quantity cannot be less than tickets already sold", status_code=400)
    for field, value in updates.items():
        setattr(ticket_type, field, value)
    session.add(ticket_type)
    session.commit()
    session.refresh(ticket_type)
    return ticket_type
