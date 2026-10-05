from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field

from model.event import EventStatus, EventType


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["Music"])


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    name: str
    created_at: datetime


class TicketTypeCreate(BaseModel):
    name: str = Field(
        max_length=100,
        examples=["VIP", "Regular", "Early Bird", "Free"],
        description="Ticket tier name",
    )
    price: int = Field(
        ge=0,
        description="Price in the smallest currency unit (e.g. kobo). Set 0 for free tickets.",
        examples=[500000, 100000, 0],
    )
    total_quantity: int = Field(
        gt=0,
        description="Total number of tickets available for this tier",
        examples=[50, 200, 100],
    )


class TicketTypeUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    price: int | None = Field(default=None, ge=0)
    total_quantity: int | None = Field(default=None, gt=0)


class TicketTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    name: str
    price: int
    total_quantity: int
    sold_quantity: int

    @computed_field
    @property
    def available_quantity(self) -> int:
        return self.total_quantity - self.sold_quantity


class EventImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    url: str
    is_primary: bool


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    host_name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    location: str = Field(min_length=1, max_length=255)
    event_date: datetime
    duration: str = Field(min_length=1, max_length=100)
    event_type: EventType
    video_url: str | None = Field(
        default=None,
        max_length=500,
        description="Optional external video URL (use the /video upload endpoint to upload a file)",
    )
    category_ids: list[UUID] = Field(default_factory=list)
    ticket_types: list[TicketTypeCreate] = Field(
        min_length=1,
        description="At least one ticket tier is required. Add multiple tiers (e.g. VIP, Regular, Free) each with their own name, price, and quantity.",
        examples=[
            [
                {"name": "VIP", "price": 500000, "total_quantity": 50},
                {"name": "Regular", "price": 150000, "total_quantity": 200},
                {"name": "Early Bird", "price": 100000, "total_quantity": 100},
            ]
        ],
    )


class EventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    host_name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1)
    location: str | None = Field(default=None, min_length=1, max_length=255)
    event_date: datetime | None = None
    duration: str | None = Field(default=None, min_length=1, max_length=100)
    event_type: EventType | None = None
    status: EventStatus | None = None
    video_url: str | None = Field(default=None, max_length=500)
    category_ids: list[UUID] | None = None


class EventImageUrlsRequest(BaseModel):
    urls: list[str] = Field(min_length=1, description="One or more image URLs to attach to the event")


class FeatureEventRequest(BaseModel):
    featured: bool


class EventOrganizerSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    first_name: str
    last_name: str
    organization: str | None = None


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    title: str
    host_name: str
    description: str
    location: str
    event_date: datetime
    duration: str
    event_type: EventType
    status: EventStatus
    featured: bool
    video_url: str | None
    organizer: EventOrganizerSummary
    categories: list[CategoryResponse] = Field(default_factory=list)
    images: list[EventImageResponse] = Field(default_factory=list)
    ticket_types: list[TicketTypeResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class EventListItem(BaseModel):
    """Public event listing card — includes cover images and description."""

    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    title: str
    description: str
    location: str
    event_date: datetime
    duration: str
    event_type: EventType
    status: EventStatus
    featured: bool
    tickets_sold: int
    images: list[EventImageResponse] = Field(default_factory=list)
