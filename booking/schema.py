from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from model.booking import OrderStatus, PaymentStatus


class BookingCreate(BaseModel):
    event_id: UUID
    ticket_type_id: UUID
    quantity: int = Field(gt=0, default=1)


class PaymentRequest(BaseModel):
    provider: str = Field(default="manual", max_length=50)
    reference: str | None = Field(default=None, max_length=200)


class BookingEventSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    title: str
    location: str
    event_date: datetime
    images: list[str] = Field(default_factory=list)

    @classmethod
    def from_event(cls, event) -> "BookingEventSummary":
        return cls(
            uuid=event.uuid,
            title=event.title,
            location=event.location,
            event_date=event.event_date,
            images=[image.url for image in event.images],
        )


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    event: BookingEventSummary
    ticket_type_id: UUID
    quantity: int
    total_amount: int
    is_free: bool
    status: OrderStatus
    created_at: datetime

    @classmethod
    def from_order(cls, order) -> "BookingResponse":
        return cls(
            uuid=order.uuid,
            event=BookingEventSummary.from_event(order.event),
            ticket_type_id=order.ticket_type_id,
            quantity=order.quantity,
            total_amount=order.total_amount,
            is_free=order.is_free,
            status=order.status,
            created_at=order.created_at,
        )


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    order_id: UUID
    amount: int
    status: PaymentStatus
    provider: str
    reference: str | None
    created_at: datetime
