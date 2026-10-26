
import re
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from database.session import engine
from model.event import Event, EventStatus


def parse_duration(duration: str) -> timedelta | None:
    """Parse durations such as '4 hours', '30 minutes', or '1 hour 30 minutes'."""
    pattern = re.compile(
        r"(\d+(?:\.\d+)?)\s*(hours?|hrs?|h|minutes?|mins?|m)",
        re.IGNORECASE,
    )

    matches = list(pattern.finditer(duration))

    if not matches:
        return None

    # Ensure the entire duration string contains only recognized components
    # and harmless separators.
    remaining = pattern.sub("", duration)
    if remaining.strip(" ,"):
        return None

    total_seconds = 0

    for match in matches:
        amount = float(match.group(1))
        unit = match.group(2).lower()

        if unit.startswith(("h", "hr")):
            total_seconds += amount * 3600
        else:
            total_seconds += amount * 60

    if total_seconds <= 0:
        return None

    return timedelta(seconds=total_seconds)


def complete_past_events() -> None:
    now = datetime.now(timezone.utc)
    candidates = 0
    skipped = 0

    with Session(engine) as session:
        events = session.exec(
            select(Event).where(Event.status == EventStatus.published)
        ).all()

        to_complete = []

        for event in events:
            duration = parse_duration(event.duration)

            if duration is None:
                print(
                    f"SKIPPED: {event.title} — "
                    f"unrecognized duration: {event.duration!r}"
                )
                skipped += 1
                continue

            # The model stores naive datetimes, so interpret stored event
            # dates as UTC. Confirm this matches your application's convention.
            event_date = event.event_date

            if event_date.tzinfo is None:
                event_date = event_date.replace(tzinfo=timezone.utc)
            else:
                event_date = event_date.astimezone(timezone.utc)

            end_time = event_date + duration

            if end_time <= now:
                to_complete.append(event)
                print(
                    f"EXPIRED: {event.title} | "
                    f"Organizer ID: {event.organizer_id} | "
                    f"Ended: {end_time.isoformat()}"
                )

        candidates = len(to_complete)

        if not to_complete:
            print("No events have passed their scheduled end time.")
            print(f"Skipped due to invalid duration: {skipped}")
            return

        print(f"\nFound {candidates} expired event(s) across all organizers.")
        print(f"Skipped due to invalid duration: {skipped}")

        confirm = input(
            "\nMark these events as completed? Type YES to continue: "
        )

        if confirm != "YES":
            print("Cancelled. No changes were made.")
            return

        for event in to_complete:
            event.status = EventStatus.completed

        session.commit()

        print(f"Updated {candidates} event(s) to completed.")


if __name__ == "__main__":
    complete_past_events()
