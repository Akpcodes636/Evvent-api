import asyncio
from io import BytesIO
from urllib.request import Request, urlopen
from uuid import UUID

from sqlmodel import Session

from database.session import engine
from event.services import get_event
from utils.cloudinary import upload_image


# ============================================================
# Unsplash source images
# ============================================================

TECH_URL = (
    "https://images.unsplash.com/"
    "photo-1510511233900-1982d92bd835"
    "?auto=format&fit=crop&w=1600&q=85"
)

PROGRAMMING_URL = (
    "https://images.unsplash.com/"
    "photo-1461749280684-dccba630e2f6"
    "?auto=format&fit=crop&w=1600&q=85"
)

MUSIC_URL = (
    "https://images.unsplash.com/"
    "photo-1501386761578-eac5c94b800a"
    "?auto=format&fit=crop&w=1600&q=85"
)

FOOTBALL_URL = (
    "https://images.unsplash.com/"
    "photo-1579952363873-27f3bade9f55"
    "?auto=format&fit=crop&w=1600&q=85"
)

THEATRE_URL = (
    "https://images.unsplash.com/"
    "photo-1503095396549-807759245b35"
    "?auto=format&fit=crop&w=1600&q=85"
)

AGRICULTURE_URL = (
    "https://images.unsplash.com/"
    "photo-1501004318641-b39e6451bec6"
    "?auto=format&fit=crop&w=1600&q=85"
)

EDUCATION_URL = (
    "https://images.unsplash.com/"
    "photo-1503676260728-1c00da094a0b"
    "?auto=format&fit=crop&w=1600&q=85"
)


# ============================================================
# Existing events with NULL image_url
# ============================================================

EVENT_IMAGES = {
    # --------------------------------------------------------
    # Tech
    # --------------------------------------------------------

    UUID("40585c54-291a-48bf-959e-e219cf8e8ac2"): TECH_URL,

    UUID("bef71dc0-95e2-4b83-b5a2-6e7285bf9716"): TECH_URL,

    UUID("24f9467d-a868-41de-b9b0-1ca05bfc5b6d"): TECH_URL,

    UUID("a119219a-8a3e-410e-abc9-2ec96f8010e6"): TECH_URL,

    UUID("307abf21-1b63-4d28-8c69-99bdc75b2622"): TECH_URL,

    # --------------------------------------------------------
    # FastAPI / Programming
    # --------------------------------------------------------

    UUID("53dd7316-dd7b-4972-b11f-db318083ea21"): PROGRAMMING_URL,

    # --------------------------------------------------------
    # Music
    # --------------------------------------------------------

    UUID("ff31481b-eb22-4c3f-be2b-2b1bc1eba282"): MUSIC_URL,

    # --------------------------------------------------------
    # Football
    # --------------------------------------------------------

    UUID("024ccd62-958c-4078-a9e9-968309ccb8bc"): FOOTBALL_URL,

    # --------------------------------------------------------
    # Theatre
    # --------------------------------------------------------

    UUID("9eed68f9-641e-4873-b745-bfe13d944aa4"): THEATRE_URL,

    UUID("d7b8ee8c-2a4e-4a7f-b518-315d03fe3f0e"): THEATRE_URL,

    # --------------------------------------------------------
    # Agriculture
    # --------------------------------------------------------

    UUID("716a972e-d867-496c-b837-abe5ce692925"): AGRICULTURE_URL,

    # --------------------------------------------------------
    # Education
    # --------------------------------------------------------

    UUID("d81f308c-3f21-4c7e-b654-c468d4f57926"): EDUCATION_URL,

    UUID("f04378c5-4cbc-4739-a9d8-7a5d30cdd481"): EDUCATION_URL,

    UUID("73474d6b-310f-44bd-aa51-59bacedb3201"): EDUCATION_URL,

    UUID("845f3a14-a820-40a0-9d82-4508fcf07773"): EDUCATION_URL,
}


def download_image(url: str) -> BytesIO:
    """
    Download an image from Unsplash into memory.

    Nothing is permanently saved to the local filesystem.
    """

    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
        },
    )

    with urlopen(request, timeout=30) as response:
        image_data = response.read()

    return BytesIO(image_data)


async def migrate():
    total = len(EVENT_IMAGES)
    successful = 0
    skipped = 0
    failed = 0

    print("=" * 70)
    print("EVENT IMAGE MIGRATION")
    print("=" * 70)
    print(f"Events to process: {total}")
    print()

    with Session(engine) as session:

        for index, (event_id, unsplash_url) in enumerate(
            EVENT_IMAGES.items(),
            start=1,
        ):
            print("-" * 70)
            print(f"[{index}/{total}] Processing {event_id}")

            try:
                # ------------------------------------------------
                # Find event
                # ------------------------------------------------

                event = get_event(session, event_id)

                print(f"Event: {event.title}")

                # ------------------------------------------------
                # Don't overwrite an existing image
                # ------------------------------------------------

                if event.image_url:
                    print("Already has an image.")
                    print("Skipping...")

                    skipped += 1
                    continue

                # ------------------------------------------------
                # Download image from Unsplash
                # ------------------------------------------------

                print("Downloading image from Unsplash...")

                image_file = await asyncio.to_thread(
                    download_image,
                    unsplash_url,
                )

                image_file.seek(0)

                print("Image downloaded.")

                # ------------------------------------------------
                # Upload to Cloudinary
                #
                # This uses your existing:
                #
                # utils/cloudinary.py
                #
                # which performs:
                # Unsplash image
                #     ↓
                # Pillow optimization
                #     ↓
                # JPEG conversion
                #     ↓
                # Cloudinary upload
                # ------------------------------------------------

                print("Uploading to Cloudinary...")

                cloudinary_url = await upload_image(
                    image_file,
                    folder=f"events/{event.uuid}",
                )

                # ------------------------------------------------
                # Save Cloudinary URL
                # ------------------------------------------------

                event.image_url = cloudinary_url

                session.add(event)
                session.commit()
                session.refresh(event)

                successful += 1

                print("✓ Migration successful")
                print(f"Cloudinary URL:")
                print(event.image_url)

            except Exception as exc:
                failed += 1

                # Roll back this event's transaction so one
                # failure doesn't poison the SQLAlchemy session.
                session.rollback()

                print("✗ Migration failed")
                print(f"Error: {exc}")

    # ============================================================
    # Summary
    # ============================================================

    print()
    print("=" * 70)
    print("MIGRATION COMPLETE")
    print("=" * 70)
    print(f"Total:      {total}")
    print(f"Successful: {successful}")
    print(f"Skipped:    {skipped}")
    print(f"Failed:     {failed}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(migrate())
