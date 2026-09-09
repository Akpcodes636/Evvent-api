from datetime import datetime
from enum import Enum
import uuid

from sqlalchemy import Column, DateTime, Enum as SqlEnum, String
from sqlmodel import Field, Relationship, SQLModel

from model.event import Event, TicketType
from model.user import User


class OrderStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    refunded = "refunded"
    cancelled = "cancelled"


class PaymentStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"


class PayoutStatus(str, Enum):
    pending = "pending"
    paid = "paid"


class Order(SQLModel, table=True):
    __tablename__ = "orders"

    uuid: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_id: uuid.UUID = Field(foreign_key="users.uuid", index=True)
    event_id: uuid.UUID = Field(foreign_key="events.uuid", index=True)
    ticket_type_id: uuid.UUID = Field(foreign_key="ticket_types.uuid", index=True)
    quantity: int = Field(gt=0)
    total_amount: int = Field(ge=0)
    is_free: bool = Field(default=False)
    status: OrderStatus = Field(
        default=OrderStatus.pending,
        sa_column=Column(SqlEnum(OrderStatus, name="order_status_enum"), nullable=False, index=True),
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, nullable=False, onupdate=datetime.utcnow),
    )

    user: User = Relationship()
    event: Event = Relationship()
    ticket_type: TicketType = Relationship()
    payment: "Payment" = Relationship(back_populates="order")


class Payment(SQLModel, table=True):
    __tablename__ = "payments"

    uuid: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    order_id: uuid.UUID = Field(foreign_key="orders.uuid", unique=True, index=True)
    amount: int = Field(ge=0)
    status: PaymentStatus = Field(
        default=PaymentStatus.pending,
        sa_column=Column(SqlEnum(PaymentStatus, name="payment_status_enum"), nullable=False, index=True),
    )
    provider: str = Field(default="manual", max_length=50)
    reference: str | None = Field(default=None, sa_column=Column(String(200), nullable=True))
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, nullable=False, onupdate=datetime.utcnow),
    )

    order: Order = Relationship(back_populates="payment")


class Payout(SQLModel, table=True):
    __tablename__ = "payouts"

    uuid: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    organizer_id: uuid.UUID = Field(foreign_key="users.uuid", index=True)
    event_id: uuid.UUID | None = Field(default=None, foreign_key="events.uuid", index=True)
    amount: int = Field(ge=0)
    status: PayoutStatus = Field(
        default=PayoutStatus.pending,
        sa_column=Column(SqlEnum(PayoutStatus, name="payout_status_enum"), nullable=False, index=True),
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, nullable=False, onupdate=datetime.utcnow),
    )

    organizer: User = Relationship()
    event: Event | None = Relationship()
