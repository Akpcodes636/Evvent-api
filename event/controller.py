
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlmodel import Session

from auth.dependencies import get_current_user, require_roles
from database.session import get_session
from event.schema import (
    CategoryCreate,
    CategoryResponse,
    EventCreate,
    EventListItem,
    EventResponse,
    EventUpdate,
    FeatureEventRequest,
    TicketTypeUpdate,
)
from event.services import (
    create_category,
    create_event,
    delete_event,
    ensure_event_access,
    feature_event,
    get_event,
    get_ticket_type,
    list_categories,
    list_events,
    list_events_for_user,
    publish_event,
    update_event,
    update_ticket_type,
)
from logger import logger
from model.event import EventStatus, EventType
from model.user import AccountType, User
from utils.cloudinary import upload_image


router = APIRouter(
    prefix="/events",
    tags=["Events"],
)

categories_router = APIRouter(
    prefix="/categories",
    tags=["Categories"],
)


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

@categories_router.get(
    "/",
    response_model=list[CategoryResponse],
)
def get_categories(
    session: Session = Depends(get_session),
) -> list[CategoryResponse]:

    categories = list_categories(session)

    return [
        CategoryResponse.model_validate(category)
        for category in categories
    ]


@categories_router.post(
    "/",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_category(
    data: CategoryCreate,
    session: Session = Depends(get_session),
    _: User = Depends(
        require_roles(
            AccountType.admin,
            AccountType.individual,
            AccountType.organization,
        )
    ),
) -> CategoryResponse:

    category = create_category(
        session,
        name=data.name,
    )

    return CategoryResponse.model_validate(category)


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_event_endpoint(
    data: Annotated[
        str,
        Form(description="EventCreate JSON payload"),
    ],
    image: Annotated[
        UploadFile,
        File(description="Event cover image"),
    ],
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_roles(
            AccountType.admin,
            AccountType.individual,
            AccountType.organization,
        )
    ),
) -> EventResponse:

    # Validate the JSON event data
    try:
        event_data = EventCreate.model_validate_json(data)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        )

    # Create the event first so we have its UUID
    event = create_event(
        session,
        host=current_user,
        data=event_data,
    )

    # Upload the single event image to Cloudinary
    cloudinary_url = await upload_image(
        image.file,
        folder=f"events/{event.uuid}",
    )

    # Store the Cloudinary URL directly on the event
    event.image_url = cloudinary_url

    session.add(event)
    session.commit()
    session.refresh(event)

    logger.info(
        "Host %s created event %s",
        current_user.uuid,
        event.uuid,
    )

    return EventResponse.model_validate(event)


@router.get(
    "/",
    response_model=list[EventListItem],
)
def list_events_endpoint(
    location: str | None = None,
    category_id: UUID | None = None,
    search: str | None = None,
    event_type: EventType | None = None,
    featured: bool | None = None,
    session: Session = Depends(get_session),
) -> list[EventListItem]:

    events = list_events(
        session,
        location=location,
        category_id=category_id,
        search=search,
        event_type=event_type,
        status=EventStatus.published,
        featured=featured,
    )

    return [
        EventListItem(
            uuid=event.uuid,
            title=event.title,
            description=event.description,
            location=event.location,
            event_date=event.event_date,
            duration=event.duration,
            event_type=event.event_type,
            status=event.status,
            featured=event.featured,
            tickets_sold=sum(
                ticket.sold_quantity
                for ticket in event.ticket_types
            ),
            image_url=event.image_url,
        )
        for event in events
    ]


@router.get(
    "/recommended",
    response_model=list[EventListItem],
)
def list_recommended_events_endpoint(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[EventListItem]:

    events = list_events_for_user(
        session,
        current_user,
    )

    return [
        EventListItem(
            uuid=event.uuid,
            title=event.title,
            description=event.description,
            location=event.location,
            event_date=event.event_date,
            duration=event.duration,
            event_type=event.event_type,
            status=event.status,
            featured=event.featured,
            tickets_sold=sum(
                ticket.sold_quantity
                for ticket in event.ticket_types
            ),
            image_url=event.image_url,
        )
        for event in events
    ]


@router.get(
    "/{event_id}",
    response_model=EventResponse,
)
def get_event_endpoint(
    event_id: UUID,
    session: Session = Depends(get_session),
) -> EventResponse:

    event = get_event(
        session,
        event_id,
    )

    return EventResponse.model_validate(event)


# ---------------------------------------------------------------------------
# Event updates
# ---------------------------------------------------------------------------

@router.patch(
    "/{event_id}",
    response_model=EventResponse,
)
def update_event_endpoint(
    event_id: UUID,
    data: EventUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> EventResponse:

    event = get_event(
        session,
        event_id,
    )

    ensure_event_access(
        event,
        current_user,
    )

    event = update_event(
        session,
        event,
        data,
    )

    logger.info(
        "User %s updated event %s",
        current_user.uuid,
        event.uuid,
    )

    return EventResponse.model_validate(event)


@router.post(
    "/{event_id}/publish",
    response_model=EventResponse,
)
def publish_event_endpoint(
    event_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> EventResponse:
    """Make an event live so it appears in the public listing."""

    event = get_event(
        session,
        event_id,
    )

    ensure_event_access(
        event,
        current_user,
    )

    event = publish_event(
        session,
        event,
    )

    logger.info(
        "User %s published event %s",
        current_user.uuid,
        event.uuid,
    )

    return EventResponse.model_validate(event)


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_event_endpoint(
    event_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:

    event = get_event(
        session,
        event_id,
    )

    ensure_event_access(
        event,
        current_user,
    )

    delete_event(
        session,
        event,
    )

    logger.info(
        "User %s deleted event %s",
        current_user.uuid,
        event_id,
    )


# ---------------------------------------------------------------------------
# Event featuring
# ---------------------------------------------------------------------------

@router.patch(
    "/{event_id}/feature",
    response_model=EventResponse,
)
def feature_event_endpoint(
    event_id: UUID,
    data: FeatureEventRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> EventResponse:

    event = get_event(
        session,
        event_id,
    )

    ensure_event_access(
        event,
        current_user,
    )

    event = feature_event(
        session,
        event,
        featured=data.featured,
    )

    logger.info(
        "User %s set event %s featured=%s",
        current_user.uuid,
        event.uuid,
        data.featured,
    )

    return EventResponse.model_validate(event)


# ---------------------------------------------------------------------------
# Event cover image
# ---------------------------------------------------------------------------

@router.patch(
    "/{event_id}/image",
    response_model=EventResponse,
)
async def update_event_image(
    event_id: UUID,
    image: Annotated[
        UploadFile,
        File(description="New event cover image"),
    ],
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> EventResponse:

    event = get_event(
        session,
        event_id,
    )

    ensure_event_access(
        event,
        current_user,
    )

    # Upload the replacement image to Cloudinary
    cloudinary_url = await upload_image(
        image.file,
        folder=f"events/{event.uuid}",
    )

    # Replace the stored URL
    event.image_url = cloudinary_url

    session.add(event)
    session.commit()
    session.refresh(event)

    logger.info(
        "User %s updated image for event %s",
        current_user.uuid,
        event_id,
    )

    return EventResponse.model_validate(event)


# ---------------------------------------------------------------------------
# Ticket types
# ---------------------------------------------------------------------------

@router.patch(
    "/{event_id}/ticket-types/{ticket_type_id}",
    response_model=EventResponse,
)
def update_ticket_type_endpoint(
    event_id: UUID,
    ticket_type_id: UUID,
    data: TicketTypeUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> EventResponse:

    event = get_event(
        session,
        event_id,
    )

    ensure_event_access(
        event,
        current_user,
    )

    ticket_type = get_ticket_type(
        session,
        event,
        ticket_type_id,
    )

    update_ticket_type(
        session,
        ticket_type,
        data,
    )

    session.refresh(event)

    logger.info(
        "User %s updated ticket type %s for event %s",
        current_user.uuid,
        ticket_type_id,
        event_id,
    )

    return EventResponse.model_validate(event)
