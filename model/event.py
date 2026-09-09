from datetime import datetime
from enum import Enum
import uuid

from sqlalchemy import Column, DateTime, Enum as SqlEnum, String, Text
from sqlmodel import Field, Relationship, SQLModel

from model.user import User


class EventType(str, Enum):
    free = "free"
    paid = "paid"


class EventStatus(str, Enum):
    draft = "draft"
    published = "published"
    completed = "completed"
    cancelled = "cancelled"


class Category(SQLModel, table=True):
    __tablename__ = "categories"

    uuid: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    name: str = Field(sa_column=Column(String(100), unique=True, nullable=False, index=True))
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))


class EventCategoryLink(SQLModel, table=True):
    __tablename__ = "event_category_links"

    event_id: uuid.UUID = Field(foreign_key="events.uuid", primary_key=True)
    category_id: uuid.UUID = Field(foreign_key="categories.uuid", primary_key=True)


class Event(SQLModel, table=True):
    __tablename__ = "events"

    uuid: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    organizer_id: uuid.UUID = Field(foreign_key="users.uuid", index=True)
    title: str = Field(max_length=200)
    host_name: str = Field(max_length=200)
    description: str = Field(sa_column=Column(Text, nullable=False))
    location: str = Field(sa_column=Column(String(255), nullable=False, index=True))
    event_date: datetime = Field(sa_column=Column(DateTime, nullable=False, index=True))
    duration: str = Field(max_length=100)
    event_type: EventType = Field(
        sa_column=Column(SqlEnum(EventType, name="event_type_enum"), nullable=False, index=True),
    )
    status: EventStatus = Field(
        default=EventStatus.draft,
        sa_column=Column(SqlEnum(EventStatus, name="event_status_enum"), nullable=False, index=True),
    )
    featured: bool = Field(default=False, index=True)
    video_url: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, nullable=False, onupdate=datetime.utcnow),
    )

    organizer: User = Relationship()
    categories: list[Category] = Relationship(link_model=EventCategoryLink)
    images: list["EventImage"] = Relationship(back_populates="event")
    ticket_types: list["TicketType"] = Relationship(back_populates="event")


class EventImage(SQLModel, table=True):
    __tablename__ = "event_images"

    uuid: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    event_id: uuid.UUID = Field(foreign_key="events.uuid", index=True)
    url: str = Field(max_length=500)
    is_primary: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))

    event: Event = Relationship(back_populates="images")


class TicketType(SQLModel, table=True):
    __tablename__ = "ticket_types"

    uuid: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    event_id: uuid.UUID = Field(foreign_key="events.uuid", index=True)
    name: str = Field(default="General", max_length=100)
    price: int = Field(ge=0, default=0)
    total_quantity: int = Field(gt=0)
    sold_quantity: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, nullable=False, onupdate=datetime.utcnow),
    )

    event: Event = Relationship(back_populates="ticket_types")
