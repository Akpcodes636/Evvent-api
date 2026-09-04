from sqlmodel import SQLModel

from database.session import engine
from model.user import User


def init_db():
    SQLModel.metadata.create_all(engine)
