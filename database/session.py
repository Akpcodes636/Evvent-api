from sqlmodel import Session, create_engine

from core.config import settings


engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
    echo=False,
)


def get_session():
    with Session(engine) as session:
        yield session
