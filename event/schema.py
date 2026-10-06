
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field

from model.event import EventStatus, EventType


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

class CategoryCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=100,
        examples=["Music"],
    )


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    name: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Ticket Types
# ---------------------------------------------------------------------------

class TicketTypeCreate(BaseModel):
    name: str = Field(
        max_length=100,
        examples=["VIP", "Regular", "Early Bird", "Free"],
        description="Ticket tier name",
    )
    price: int = Field(
        ge=0,
        description=(
            "Price in the smallest currency unit "
            "(e.g. kobo). Set 0 for free tickets."
        ),
        examples=[500000, 100000, 0],
    )
    total_quantity: int = Field(
        gt=0,
        description="Total number of tickets available for this tier",
        examples=[50, 200, 100],
    )


class TicketTypeUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        max_length=100,
    )
    price: int | None = Field(
        default=None,
        ge=0,
    )
    total_quantity: int | None = Field(
        default=None,
        gt=0,
    )


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


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

class EventCreate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=200,
    )
    host_name: str = Field(
        min_length=1,
        max_length=200,
    )
    description: str = Field(
        min_length=1,
    )
    location: str = Field(
        min_length=1,
        max_length=255,
    )
    event_date: datetime
    duration: str = Field(
        min_length=1,
        max_length=100,
    )
    event_type: EventType

    category_ids: list[UUID] = Field(
        default_factory=list,
    )

    ticket_types: list[TicketTypeCreate] = Field(
        min_length=1,
        description="At least one ticket tier is required.",
        examples=[
            [
                {
                    "name": "VIP",
                    "price": 500000,
                    "total_quantity": 50,
                },
                {
                    "name": "Regular",
                    "price": 150000,
                    "total_quantity": 200,
                },
                {
                    "name": "Early Bird",
                    "price": 100000,
                    "total_quantity": 100,
                },
            ]
        ],
    )


class EventUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    host_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    description: str | None = Field(
        default=None,
        min_length=1,
    )
    location: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    event_date: datetime | None = None
    duration: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    event_type: EventType | None = None
    status: EventStatus | None = None
    category_ids: list[UUID] | None = None


class FeatureEventRequest(BaseModel):
    featured: bool


# ---------------------------------------------------------------------------
# Organizer
# ---------------------------------------------------------------------------

class EventOrganizerSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    first_name: str
    last_name: str
    organization: str | None = None


# ---------------------------------------------------------------------------
# Event Responses
# ---------------------------------------------------------------------------

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

    # Cloudinary URL for the event's single cover image
    image_url: str

    organizer: EventOrganizerSummary

    categories: list[CategoryResponse] = Field(
        default_factory=list,
    )

    ticket_types: list[TicketTypeResponse] = Field(
        default_factory=list,
    )

    created_at: datetime
    updated_at: datetime


class EventListItem(BaseModel):
    """
    Public event listing card.
    Contains the event's single Cloudinary cover image.
    """

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

    # Cloudinary URL for the event's single cover image
    image_url: str
