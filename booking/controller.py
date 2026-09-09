from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from auth.dependencies import get_current_user
from booking.schema import BookingCreate, BookingResponse, PaymentRequest, PaymentResponse
from booking.services import cancel_booking, create_booking, get_booking, list_user_bookings, pay_booking
from database.session import get_session
from logger import logger
from model.user import User

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking_endpoint(
    data: BookingCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> BookingResponse:
    order = create_booking(session, current_user, **data.model_dump())
    logger.info("User %s booked event %s (order %s)", current_user.uuid, data.event_id, order.uuid)
    return BookingResponse.from_order(order)


@router.get("/me", response_model=list[BookingResponse])
def list_my_bookings(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[BookingResponse]:
    return [BookingResponse.from_order(o) for o in list_user_bookings(session, current_user)]


@router.get("/{order_id}", response_model=BookingResponse)
def get_booking_endpoint(
    order_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> BookingResponse:
    order = get_booking(session, current_user, order_id)
    return BookingResponse.from_order(order)


@router.post("/{order_id}/pay", response_model=PaymentResponse)
def pay_booking_endpoint(
    order_id: UUID,
    data: PaymentRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> PaymentResponse:
    order = pay_booking(session, current_user, order_id, **data.model_dump())
    logger.info("User %s paid for booking %s", current_user.uuid, order_id)
    return PaymentResponse.model_validate(order.payment)


@router.post("/{order_id}/cancel", response_model=BookingResponse)
def cancel_booking_endpoint(
    order_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> BookingResponse:
    order = cancel_booking(session, current_user, order_id)
    logger.info("User %s cancelled booking %s", current_user.uuid, order_id)
    return BookingResponse.from_order(order)
