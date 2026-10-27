"""
Celery background tasks for sending emails.

To start the worker:
    celery -A worker.celery_app worker --loglevel=info
"""
from __future__ import annotations

import uuid

from sqlmodel import Session, select

from database.session import engine
from logger import logger
from utils.email import send_booking_confirmation_email, send_welcome_email
from worker.celery_app import celery_app


# ---------------------------------------------------------------------------
# Welcome / invite email
# ---------------------------------------------------------------------------

@celery_app.task(name="tasks.send_welcome_email", bind=True, max_retries=3, default_retry_delay=60)
def task_send_welcome_email(self, to_email: str, first_name: str) -> None:
    """Send a welcome/invite email to a newly registered user."""
    try:
        send_welcome_email(to_email=to_email, first_name=first_name)
        logger.info("Welcome email dispatched to %s", to_email)
    except Exception as exc:
        logger.exception("Welcome email failed for %s, retrying…", to_email)
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# Booking confirmation email
# ---------------------------------------------------------------------------

@celery_app.task(name="tasks.send_booking_confirmation", bind=True, max_retries=3, default_retry_delay=60)
def task_send_booking_confirmation(self, order_id: str) -> None:
    """
    Fetch order details from the database and send a confirmation email to
    every attendee on the booking.

    Called after a booking is completed (free booking, Paystack webhook, or
    manual payment confirmation).
    """
    from model.booking import AttendeeDetail, Order

    try:
        with Session(engine) as session:
            order = session.get(Order, uuid.UUID(order_id))
            if not order:
                logger.warning("task_send_booking_confirmation: order %s not found", order_id)
                return

            event = order.event
            ticket_type = order.ticket_type
            user = order.user

            attendees = list(
                session.exec(
                    select(AttendeeDetail)
                    .where(AttendeeDetail.order_id == order.uuid)
                    .order_by(AttendeeDetail.ticket_index)
                ).all()
            )

        # Build the shared attendee list shown inside every email
        all_attendees = [
            {"name": f"{a.first_name} {a.last_name}".strip(), "email": a.email}
            for a in attendees
        ]

        # Format event date for display
        event_date_str = event.event_date.strftime("%A, %B %-d %Y · %I:%M %p")
        order_ref = str(order.uuid).upper()[:8]

        # Send one email per attendee (each attendee gets a personalised copy)
        recipients = attendees if attendees else None
        if recipients:
            for attendee in recipients:
                send_booking_confirmation_email(
                    to_email=attendee.email,
                    attendee_name=f"{attendee.first_name} {attendee.last_name}".strip(),
                    event_title=event.title,
                    event_date=event_date_str,
                    event_location=event.location,
                    event_duration=event.duration,
                    ticket_type_name=ticket_type.name,
                    quantity=order.quantity,
                    total_amount=order.total_amount,
                    order_ref=order_ref,
                    all_attendees=all_attendees,
                )
        else:
            # Fallback: send to the account owner if no attendee records exist
            send_booking_confirmation_email(
                to_email=user.email,
                attendee_name=f"{user.first_name} {user.last_name}".strip(),
                event_title=event.title,
                event_date=event_date_str,
                event_location=event.location,
                event_duration=event.duration,
                ticket_type_name=ticket_type.name,
                quantity=order.quantity,
                total_amount=order.total_amount,
                order_ref=order_ref,
                all_attendees=all_attendees,
            )

        logger.info(
            "Booking confirmation emails sent for order %s (%d recipient(s))",
            order_id,
            len(all_attendees) or 1,
        )

    except Exception as exc:
        logger.exception("Booking confirmation email failed for order %s, retrying…", order_id)
        raise self.retry(exc=exc)
