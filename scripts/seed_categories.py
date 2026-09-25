from sqlmodel import Session, select

from database.session import engine
from model.event import Category


CATEGORIES = [
    "Music",
    "Business",
    "Technology",
    "Sports",
    "Food & Drink",
    "Arts & Culture",
    "Health & Wellness",
    "Education",
    "Religion",
    "Fashion",
    "Travel",
    "Comedy",
    "Networking",
]


def seed_categories():
    with Session(engine) as session:

        for name in CATEGORIES:

            existing = session.exec(
                select(Category)
                .where(Category.name == name)
            ).first()

            if existing:
                continue

            session.add(
                Category(name=name)
            )

        session.commit()


if __name__ == "__main__":
    seed_categories()
