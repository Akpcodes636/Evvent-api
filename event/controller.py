from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlmodel import Session

from auth.dependencies import get_current_user, require_roles
from database.session import get_session
from event.schema import (
    CategoryCreate, CategoryResponse, EventCreate, EventImageResponse, EventListItem,
    EventResponse, EventUpdate, FeatureEventRequest, TicketTypeUpdate,
)
from event.services import (
    add_event_images, create_category, create_event, delete_event, delete_event_image,
    ensure_event_access, feature_event, get_event, get_ticket_type, list_categories,
    list_events, update_event, update_ticket_type,
)
from logger import logger
from model.event import EventStatus, EventType
from model.user import User, UserRole
from utils.uploads import IMAGE_CONTENT_TYPES, VIDEO_CONTENT_TYPES, save_upload

router = APIRouter(prefix="/events", tags=["Events"])
categories_router = APIRouter(prefix="/categories", tags=["Categories"])


@categories_router.get("/", response_model=list[CategoryResponse])
def get_categories(session: Session = Depends(get_session)) -> list[CategoryResponse]:
    return [CategoryResponse.model_validate(c) for c in list_categories(session)]


@categories_router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def add_category(
    data: CategoryCreate,
    session: Session = Depends(get_session),
    _: User = Depends(require_roles(UserRole.admin, UserRole.organizer)),
) -> CategoryResponse:
    category = create_category(session, name=data.name)
    return CategoryResponse.model_validate(category)


@router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event_endpoint(
    data: EventCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.organizer)),
) -> EventResponse:
    event = create_event(session, organizer=current_user, data=data)
    logger.info("Organizer %s created event %s", current_user.uuid, event.uuid)
    return EventResponse.model_validate(event)


@router.get("/", response_model=list[EventListItem])
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
            uuid=e.uuid, title=e.title, event_date=e.event_date, status=e.status,
            tickets_sold=sum(t.sold_quantity for t in e.ticket_types),
            featured=e.featured,
        )
        for e in events
    ]


@router.get("/{event_id}", response_model=EventResponse)
def get_event_endpoint(event_id: UUID, session: Session = Depends(get_session)) -> EventResponse:
    event = get_event(session, event_id)
    return EventResponse.model_validate(event)


@router.patch("/{event_id}", response_model=EventResponse)
def update_event_endpoint(
    event_id: UUID,
    data: EventUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> EventResponse:
    event = get_event(session, event_id)
    ensure_event_access(event, current_user)
    event = update_event(session, event, data)
    logger.info("User %s updated event %s", current_user.uuid, event.uuid)
    return EventResponse.model_validate(event)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event_endpoint(
    event_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    event = get_event(session, event_id)
    ensure_event_access(event, current_user)
    delete_event(session, event)
    logger.info("User %s deleted event %s", current_user.uuid, event_id)


@router.patch("/{event_id}/feature", response_model=EventResponse)
def feature_event_endpoint(
    event_id: UUID,
    data: FeatureEventRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles(UserRole.admin)),
) -> EventResponse:
    event = get_event(session, event_id)
    event = feature_event(session, event, featured=data.featured)
    logger.info("Admin %s set event %s featured=%s", current_user.uuid, event.uuid, data.featured)
    return EventResponse.model_validate(event)


@router.post("/{event_id}/images", response_model=list[EventImageResponse], status_code=status.HTTP_201_CREATED)
async def upload_event_images(
    event_id: UUID,
    files: list[UploadFile] = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[EventImageResponse]:
    event = get_event(session, event_id)
    ensure_event_access(event, current_user)
    urls = [await save_upload(f, subdir=f"events/{event_id}/images", allowed_types=IMAGE_CONTENT_TYPES) for f in files]
    images = add_event_images(session, event, urls)
    logger.info("User %s uploaded %d image(s) for event %s", current_user.uuid, len(images), event_id)
    return [EventImageResponse.model_validate(i) for i in images]


@router.delete("/{event_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event_image_endpoint(
    event_id: UUID,
    image_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    event = get_event(session, event_id)
    ensure_event_access(event, current_user)
    delete_event_image(session, event, image_id)


@router.post("/{event_id}/video", response_model=EventResponse)
async def upload_event_video(
    event_id: UUID,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> EventResponse:
    event = get_event(session, event_id)
    ensure_event_access(event, current_user)
    event.video_url = await save_upload(file, subdir=f"events/{event_id}/video", allowed_types=VIDEO_CONTENT_TYPES)
    session.add(event)
    session.commit()
    session.refresh(event)
    logger.info("User %s uploaded a video for event %s", current_user.uuid, event_id)
    return EventResponse.model_validate(event)


@router.patch("/{event_id}/ticket-types/{ticket_type_id}", response_model=EventResponse)
def update_ticket_type_endpoint(
    event_id: UUID,
    ticket_type_id: UUID,
    data: TicketTypeUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> EventResponse:
    event = get_event(session, event_id)
    ensure_event_access(event, current_user)
    ticket_type = get_ticket_type(session, event, ticket_type_id)
    update_ticket_type(session, ticket_type, data)
    session.refresh(event)
    logger.info("User %s updated ticket type %s for event %s", current_user.uuid, ticket_type_id, event_id)
    return EventResponse.model_validate(event)
