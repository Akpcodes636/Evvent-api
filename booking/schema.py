from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from model.booking import OrderStatus, PaymentStatus


# ---------------------------------------------------------------------------
# Attendee Details
# ---------------------------------------------------------------------------

class AttendeeDetailCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100, examples=["John"])
    last_name: str = Field(min_length=1, max_length=100, examples=["Doe"])
    email: EmailStr = Field(examples=["john@example.com"])
    confirm_email: EmailStr = Field(examples=["john@example.com"])
    phone: str = Field(
        min_length=7,
        max_length=32,
        examples=["+2348012345678"],
        description="Attendee's phone number",
    )

    @model_validator(mode="after")
    def emails_must_match(self) -> "AttendeeDetailCreate":
        if self.email != self.confirm_email:
            raise ValueError("Email addresses do not match")
        return self


class AttendeeDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    ticket_index: int
    first_name: str
    last_name: str
    email: str
    phone: str


# ---------------------------------------------------------------------------
# Booking
# ---------------------------------------------------------------------------

class BookingCreate(BaseModel):
    event_id: UUID
    ticket_type_id: UUID
    quantity: int = Field(gt=0, default=1, le=20, description="Maximum 20 tickets per order")
    attendees: list[AttendeeDetailCreate] = Field(
        min_length=1,
        description="One set of attendee details per ticket. Length must equal quantity.",
        examples=[
            [
                {
                    "first_name": "John",
                    "last_name": "Doe",
                    "email": "john@example.com",
                    "confirm_email": "john@example.com",
                    "phone": "+2348012345678",
                }
            ]
        ],
    )

    @model_validator(mode="after")
    def attendees_match_quantity(self) -> "BookingCreate":
        if len(self.attendees) != self.quantity:
            raise ValueError(
                f"Number of attendee details ({len(self.attendees)}) "
                f"must equal the ticket quantity ({self.quantity})"
            )
        return self


class PaymentRequest(BaseModel):
    provider: str = Field(default="manual", max_length=50)
    reference: str | None = Field(default=None, max_length=200)


# ---------------------------------------------------------------------------
# Booking Responses
# ---------------------------------------------------------------------------

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
            images=[event.image_url] if event.image_url else [],
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


# ---------------------------------------------------------------------------
# Payment Responses
# ---------------------------------------------------------------------------

class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    order_id: UUID
    amount: int
    status: PaymentStatus
    provider: str
    reference: str | None
    created_at: datetime


class PaystackInitResponse(BaseModel):
    """Returned when a Paystack payment is initialized."""

    order_id: UUID
    authorization_url: str
    access_code: str
    reference: str
    amount: int
    message: str = "Payment initialized. Redirect the user to the authorization_url to complete payment."


class PaystackWebhookPayload(BaseModel):
    """Minimal Paystack webhook body we care about."""

    event: str
    data: dict
