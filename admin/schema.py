from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from model.booking import OrderStatus, PayoutStatus
from model.event import EventStatus


class DashboardStats(BaseModel):
    total_events: int
    active_events: int
    upcoming_events: int
    total_tickets_sold: int
    total_revenue: int


class OrderStats(BaseModel):
    total_orders: int
    pending_orders: int
    completed_orders: int
    refunded_orders: int
    free_orders: int


class OrderListItem(BaseModel):
    order_id: UUID
    event: str
    buyer: str
    tickets: int
    total: int
    type: str
    status: OrderStatus
    date: datetime


class FinanceStats(BaseModel):
    total_revenue: int
    available_balance: int
    pending: int
    total_events: int


class PayoutListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    date: datetime = Field(validation_alias="created_at")
    event: str | None = None
    amount: int
    status: PayoutStatus
    type: str = "payout"


class PayoutCreate(BaseModel):
    organizer_id: UUID
    event_id: UUID | None = None
    amount: int = Field(gt=0)


class PayoutStatusUpdate(BaseModel):
    status: PayoutStatus


class OrganizerListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    first_name: str
    last_name: str
    email: str
    phone: str | None
    organization: str | None
    created_at: datetime


class OrganizerUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = None
    phone: str | None = Field(default=None, min_length=1, max_length=32)
    organization: str | None = Field(default=None, max_length=200)


class AdminEventListItem(BaseModel):
    uuid: UUID
    title: str
    date: datetime
    status: EventStatus
    tickets_sold: int
    featured: bool
